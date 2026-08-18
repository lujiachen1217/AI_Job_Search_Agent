"""LLM-based final application decision analysis for shortlisted jobs."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from numbers import Integral

import pandas as pd

from src.clients.openai_client import get_openai_client


JOB_DECISIONS = {"APPLY", "MAYBE", "SKIP"}
DEFAULT_JOB_DECISION = {
    "decision": "MAYBE",
    "confidence": 0,
    "reason": "Job decision analysis unavailable",
    "strengths": [],
    "concerns": [],
}


def _validate_string_list(value: object, field_name: str) -> list[str]:
    """Validate a JSON list containing only non-empty strings."""
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{field_name} must contain only non-empty strings")
    return [item.strip() for item in value]


def _validate_job_decision(result: object) -> dict:
    """Validate and normalize a structured job decision response."""
    if not isinstance(result, dict):
        raise ValueError("Job decision response must be a JSON object")

    decision = result.get("decision")
    confidence = result.get("confidence")
    reason = result.get("reason")

    if decision not in JOB_DECISIONS:
        raise ValueError("Invalid job decision")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, Integral)
        or not 0 <= confidence <= 100
    ):
        raise ValueError("Decision confidence must be an integer from 0 to 100")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Decision reason must be a non-empty string")

    return {
        "decision": decision,
        "confidence": int(confidence),
        "reason": reason.strip(),
        "strengths": _validate_string_list(result.get("strengths"), "strengths"),
        "concerns": _validate_string_list(result.get("concerns"), "concerns"),
    }


def analyze_job_decision(
    candidate_profile: dict,
    company: str,
    title: str,
    location: str,
    job_description: str,
    match_score: float,
    ai_match_score: object,
    final_match_score: object,
    matched_skills: str,
    missing_skills: str,
    sponsorship_status: str,
    sponsorship_confidence: int,
    sponsorship_reason: str,
) -> dict:
    """Decide whether one shortlisted job is worth applying to."""
    prompt = f"""
You are a practical job application advisor for an early-career candidate.

Decide whether applying to this specific job is worth the candidate's time.
Return APPLY, MAYBE, or SKIP. This is a qualitative application decision, not
another generic match score.

Use the existing scores as useful signals, but do not mechanically translate
them into a decision. The candidate does not need to meet every requirement.
An APPLY decision can still be appropriate when individual tools, libraries,
cloud products, visualization tools, or platforms are missing if the core
analytical and programming fit is strong and those gaps appear learnable.

Consider:
1. Core fit in Python, R, SQL, statistics, machine learning, data analysis,
   and other relevant quantitative skills.
2. Education fit using only the supplied candidate profile.
3. Experience and seniority fit, including required years, management duties,
   senior/staff/lead expectations, and required PhD-level qualifications.
4. Whether missing qualifications are critical or realistically learnable.
5. Match Score, AI Match Score, and Final Match Score as supporting signals.
6. Job-specific sponsorship evidence.

Treat required education, required years of experience, required domain
expertise, and required work authorization as potentially critical gaps.

If Sponsorship Status is "Likely No" with high confidence and explicit
evidence, treat it as a major concern. "Unknown" means insufficient evidence
and must not automatically result in SKIP. "Likely Yes" may strengthen the
decision.

Do not invent candidate qualifications or employer policies. Be practical and
avoid being overly conservative. Keep the reason concise.

Return ONLY valid JSON using exactly this structure:

{{
  "decision": "MAYBE",
  "confidence": 0,
  "reason": "",
  "strengths": [],
  "concerns": []
}}

The decision must be exactly "APPLY", "MAYBE", or "SKIP".
The confidence must be an integer from 0 to 100.
Strengths and concerns must be JSON arrays of concise strings and may be empty.

Candidate profile:
{json.dumps(candidate_profile, ensure_ascii=False)}

Company: {company}
Job title: {title}
Location: {location}

Job description:
{job_description}

Match Score: {match_score}
AI Match Score: {ai_match_score}
Final Match Score: {final_match_score}
Matched Skills: {matched_skills}
Missing Skills: {missing_skills}

Sponsorship Status: {sponsorship_status}
Sponsorship Confidence: {sponsorship_confidence}
Sponsorship Reason: {sponsorship_reason}
"""

    try:
        response = get_openai_client().responses.create(
            model="gpt-5",
            input=prompt,
        )
        result = json.loads(response.output_text)
        return _validate_job_decision(result)
    except Exception as error:
        print(f"Job decision analysis failed for {company} - {title}: {error}")
        return {
            **DEFAULT_JOB_DECISION,
            "strengths": [],
            "concerns": [],
        }


def add_job_decisions(
    jobs_dataframe: pd.DataFrame,
    candidate_profile: dict,
    top_n: int = 5,
    max_workers: int = 4,
) -> pd.DataFrame:
    """Concurrently add final LLM decisions to the Top N shortlisted jobs."""
    if max_workers < 1:
        raise ValueError("max_workers must be at least 1")

    jobs_dataframe = jobs_dataframe.copy().reset_index(drop=True)
    jobs_dataframe["LLM Decision"] = ""
    jobs_dataframe["Decision Confidence"] = None
    jobs_dataframe["Decision Reason"] = ""
    jobs_dataframe["Decision Strengths"] = ""
    jobs_dataframe["Decision Concerns"] = ""

    analyzed_count = min(top_n, len(jobs_dataframe))
    if analyzed_count:
        worker_count = min(max_workers, analyzed_count)
        future_to_job: dict = {}

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            for index in range(analyzed_count):
                row = jobs_dataframe.iloc[index]
                print(
                    f"\n正在提交最终 LLM 决策："
                    f"{row['Company']} - {row['Title']}"
                )
                future = executor.submit(
                    analyze_job_decision,
                    candidate_profile=candidate_profile,
                    company=row["Company"],
                    title=row["Title"],
                    location=row["Location"],
                    job_description=row["Job Description"],
                    match_score=row["Match Score"],
                    ai_match_score=row["AI Match Score"],
                    final_match_score=row["Final Match Score"],
                    matched_skills=row["Matched Skills"],
                    missing_skills=row["Missing Skills"],
                    sponsorship_status=row["Sponsorship Status"],
                    sponsorship_confidence=row["Sponsorship Confidence"],
                    sponsorship_reason=row["Sponsorship Reason"],
                )
                future_to_job[future] = {
                    "index": index,
                    "company": row["Company"],
                    "title": row["Title"],
                }

            for future in as_completed(future_to_job):
                job = future_to_job[future]
                index = job["index"]
                try:
                    result = future.result()
                except Exception as error:
                    print(
                        "Job decision analysis failed for "
                        f"{job['company']} - {job['title']}: {error}"
                    )
                    result = {
                        **DEFAULT_JOB_DECISION,
                        "strengths": [],
                        "concerns": [],
                    }

                jobs_dataframe.at[index, "LLM Decision"] = result["decision"]
                jobs_dataframe.at[index, "Decision Confidence"] = result[
                    "confidence"
                ]
                jobs_dataframe.at[index, "Decision Reason"] = result["reason"]
                jobs_dataframe.at[index, "Decision Strengths"] = ", ".join(
                    result["strengths"]
                )
                jobs_dataframe.at[index, "Decision Concerns"] = ", ".join(
                    result["concerns"]
                )

                print(
                    f"最终决策完成：{job['company']} - {job['title']}"
                )
                print(
                    f"Decision：{result['decision']} | "
                    f"Confidence：{result['confidence']}"
                )
                print(f"Reason：{result['reason']}")

    return jobs_dataframe
