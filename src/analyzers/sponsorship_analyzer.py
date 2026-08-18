"""LLM-based analysis of job-specific visa sponsorship evidence."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from numbers import Integral

import pandas as pd

from src.clients.openai_client import get_openai_client


SPONSORSHIP_STATUSES = {"Likely Yes", "Likely No", "Unknown"}
DEFAULT_SPONSORSHIP_RESULT = {
    "sponsorship_status": "Unknown",
    "confidence": 0,
    "reason": "Sponsorship analysis unavailable",
    "evidence": "",
}


def _validate_sponsorship_result(result: object) -> dict:
    """Validate and normalize the structured sponsorship response."""
    if not isinstance(result, dict):
        raise ValueError("Sponsorship response must be a JSON object")

    status = result.get("sponsorship_status")
    confidence = result.get("confidence")
    reason = result.get("reason")
    evidence = result.get("evidence")

    if status not in SPONSORSHIP_STATUSES:
        raise ValueError("Invalid sponsorship status")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, Integral)
        or not 0 <= confidence <= 100
    ):
        raise ValueError("Sponsorship confidence must be an integer from 0 to 100")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Sponsorship reason must be a non-empty string")
    if not isinstance(evidence, str):
        raise ValueError("Sponsorship evidence must be a string")

    return {
        "sponsorship_status": status,
        "confidence": int(confidence),
        "reason": reason.strip(),
        "evidence": evidence.strip(),
    }


def analyze_sponsorship(
    company: str,
    title: str,
    location: str,
    job_description: str,
) -> dict:
    """Analyze sponsorship evidence for one job and return a safe result."""
    prompt = f"""
You are a conservative US employment visa sponsorship analyst.

Determine whether this specific job appears willing to consider a candidate
who may require US employment visa sponsorship. Base the decision primarily
on explicit evidence in the job description. Do not rely on the company's
general reputation or assume that a company sponsors all roles.

Decision rules:

- "Likely No": The job explicitly says that visa sponsorship is unavailable,
  the employer cannot or will not sponsor, or the candidate must already have
  unrestricted work authorization.
- "Likely Yes": The job explicitly says that sponsorship, visa support, or
  visa transfer is available, or that candidates requiring sponsorship will
  be considered.
- "Unknown": The job does not contain enough reliable evidence. Silence about
  sponsorship must be classified as "Unknown", not "Likely Yes".

Act conservatively. Distinguish explicit evidence from assumptions. Do not
invent policies or facts. Keep the reason and evidence concise. Evidence may
be a short excerpt or a faithful paraphrase from the job description.

Return ONLY valid JSON using exactly this structure:

{{
  "sponsorship_status": "Unknown",
  "confidence": 0,
  "reason": "",
  "evidence": ""
}}

The sponsorship_status must be exactly one of:
"Likely Yes", "Likely No", or "Unknown".
The confidence must be an integer from 0 to 100.

Company:
{company}

Job title:
{title}

Location:
{location}

Full job description:
{job_description}
"""

    try:
        response = get_openai_client().responses.create(
            model="gpt-5",
            input=prompt,
        )
        result = json.loads(response.output_text)
        return _validate_sponsorship_result(result)
    except Exception as error:
        print(
            "Sponsorship analysis failed for "
            f"{company} - {title}: {error}"
        )
        return DEFAULT_SPONSORSHIP_RESULT.copy()


def add_sponsorship_analysis(
    jobs_dataframe: pd.DataFrame,
    top_n: int = 5,
    max_workers: int = 4,
) -> pd.DataFrame:
    """Concurrently add sponsorship analysis to the Top N shortlisted jobs."""
    if max_workers < 1:
        raise ValueError("max_workers must be at least 1")

    jobs_dataframe = jobs_dataframe.copy().reset_index(drop=True)
    jobs_dataframe["Sponsorship Status"] = "Unknown"
    jobs_dataframe["Sponsorship Confidence"] = 0
    jobs_dataframe["Sponsorship Reason"] = ""
    jobs_dataframe["Sponsorship Evidence"] = ""

    analyzed_count = min(top_n, len(jobs_dataframe))
    if analyzed_count:
        worker_count = min(max_workers, analyzed_count)
        future_to_job: dict = {}

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            for index in range(analyzed_count):
                row = jobs_dataframe.iloc[index]
                print(
                    f"\n正在提交 Sponsorship 分析："
                    f"{row['Company']} - {row['Title']}"
                )
                future = executor.submit(
                    analyze_sponsorship,
                    company=row["Company"],
                    title=row["Title"],
                    location=row["Location"],
                    job_description=row["Job Description"],
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
                        "Sponsorship analysis failed for "
                        f"{job['company']} - {job['title']}: {error}"
                    )
                    result = DEFAULT_SPONSORSHIP_RESULT.copy()

                jobs_dataframe.at[index, "Sponsorship Status"] = result[
                    "sponsorship_status"
                ]
                jobs_dataframe.at[index, "Sponsorship Confidence"] = result[
                    "confidence"
                ]
                jobs_dataframe.at[index, "Sponsorship Reason"] = result["reason"]
                jobs_dataframe.at[index, "Sponsorship Evidence"] = result[
                    "evidence"
                ]

                print(
                    f"Sponsorship 分析完成："
                    f"{job['company']} - {job['title']}"
                )
                print(
                    f"Sponsorship：{result['sponsorship_status']} | "
                    f"Confidence：{result['confidence']}"
                )
                print(f"Reason：{result['reason']}")

    return jobs_dataframe
