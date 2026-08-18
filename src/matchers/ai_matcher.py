import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from src.clients.openai_client import get_openai_client


def calculate_final_score(keyword_score: float, ai_score: float) -> float:
    """Combine keyword and AI match scores using their configured weights."""
    return round(keyword_score * 0.4 + ai_score * 0.6, 1)


def calculate_ai_match(
    resume_data: dict,
    job_title: str,
    job_description: str,
) -> dict:
    """使用 GPT 对结构化简历和职位描述进行语义匹配。"""
    prompt = f"""
You are an experienced technical recruiter evaluating an early-career
candidate for a job.

Evaluate the candidate against the job description using semantic matching.
Do not rely only on exact keyword matches.

Consider:

1. Technical skills
2. Statistical and analytical knowledge
3. Education
4. Relevant work and project experience
5. Required years of experience
6. Seniority level
7. Industry relevance

Scoring guide:

90-100:
The candidate meets nearly all major requirements.

75-89:
The candidate is a strong match but has a few manageable gaps.

60-74:
The candidate is a reasonable match and may be worth applying.

40-59:
The candidate has some relevant qualifications but has major gaps.

0-39:
The candidate is not currently a strong match.

Return ONLY valid JSON using exactly this structure:

{{
  "ai_match_score": 0,
  "recommendation": "",
  "matched_qualifications": [],
  "missing_qualifications": [],
  "reasoning": []
}}

The recommendation must be exactly one of:

75-100: "Strong Apply"
60-74: "Apply"
45-59: "Maybe"
0-44: "Do Not Apply"

Candidate resume:

{json.dumps(resume_data, ensure_ascii=False)}

Job title:

{job_title}

Job description:

{job_description}
"""
    response = get_openai_client().responses.create(model="gpt-5", input=prompt)
    return json.loads(response.output_text)


def add_ai_match_scores(
    jobs_dataframe: pd.DataFrame,
    resume_data: dict,
    top_n: int = 5,
    max_workers: int = 4,
) -> pd.DataFrame:
    """Concurrently add GPT match results to the highest-ranked Top N jobs."""
    if max_workers < 1:
        raise ValueError("max_workers must be at least 1")

    jobs_dataframe = jobs_dataframe.copy().reset_index(drop=True)
    jobs_dataframe["AI Match Score"] = None
    jobs_dataframe["Final Match Score"] = None
    jobs_dataframe["Recommendation"] = ""
    jobs_dataframe["AI Matched Qualifications"] = ""
    jobs_dataframe["AI Missing Qualifications"] = ""
    jobs_dataframe["AI Reasoning"] = ""

    analyzed_count = min(top_n, len(jobs_dataframe))
    if analyzed_count:
        worker_count = min(max_workers, analyzed_count)
        future_to_job: dict = {}

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            for index in range(analyzed_count):
                row = jobs_dataframe.iloc[index]
                print(
                    f"\n正在提交 AI 匹配："
                    f"{row['Company']} - {row['Title']}"
                )
                future = executor.submit(
                    calculate_ai_match,
                    resume_data=resume_data,
                    job_title=row["Title"],
                    job_description=row["Job Description"],
                )
                future_to_job[future] = {
                    "index": index,
                    "company": row["Company"],
                    "title": row["Title"],
                    "match_score": row["Match Score"],
                }

            for future in as_completed(future_to_job):
                job = future_to_job[future]
                index = job["index"]

                try:
                    ai_result = future.result()
                    ai_score = ai_result.get("ai_match_score")
                    jobs_dataframe.at[index, "AI Match Score"] = ai_score

                    try:
                        numeric_ai_score = float(ai_score)
                        if isinstance(ai_score, bool) or not math.isfinite(
                            numeric_ai_score
                        ) or not 0 <= numeric_ai_score <= 100:
                            raise ValueError(
                                "AI match score must be between 0 and 100"
                            )
                        jobs_dataframe.at[index, "Final Match Score"] = (
                            calculate_final_score(
                                float(job["match_score"]), numeric_ai_score
                            )
                        )
                    except (TypeError, ValueError):
                        jobs_dataframe.at[index, "Final Match Score"] = None

                    jobs_dataframe.at[index, "Recommendation"] = ai_result.get(
                        "recommendation", ""
                    )
                    jobs_dataframe.at[
                        index, "AI Matched Qualifications"
                    ] = ", ".join(ai_result.get("matched_qualifications", []))
                    jobs_dataframe.at[
                        index, "AI Missing Qualifications"
                    ] = ", ".join(ai_result.get("missing_qualifications", []))
                    jobs_dataframe.at[index, "AI Reasoning"] = " | ".join(
                        ai_result.get("reasoning", [])
                    )
                    print(
                        f"AI 匹配完成：{job['company']} - {job['title']}"
                    )
                    print(
                        f"AI Score：{ai_result.get('ai_match_score')} | "
                        f"Recommendation："
                        f"{ai_result.get('recommendation', '')}"
                    )
                except Exception as error:
                    print(
                        f"AI 匹配失败：{job['company']} - "
                        f"{job['title']}：{error}"
                    )
    analyzed_jobs = jobs_dataframe.iloc[:analyzed_count].sort_values(
        by="Final Match Score",
        ascending=False,
        na_position="last",
        kind="stable",
    )
    remaining_jobs = jobs_dataframe.iloc[analyzed_count:]
    jobs_dataframe = pd.concat(
        [analyzed_jobs, remaining_jobs], ignore_index=True
    )

    return jobs_dataframe
