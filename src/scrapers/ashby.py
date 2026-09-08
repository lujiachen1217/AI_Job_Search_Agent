"""Ashby public job-board scraper."""

from collections.abc import Iterable

import pandas as pd
import requests

from src.config import ASHBY_COMPANIES
from src.scrapers.greenhouse import SCRAPED_JOB_COLUMNS, clean_job_description


ASHBY_JOB_BOARD_URL = "https://api.ashbyhq.com/posting-api/job-board/{company}"


def normalize_ashby_job(company: str, job: dict) -> dict | None:
    """Normalize one Ashby posting to the shared job schema."""
    if not isinstance(job, dict):
        return None

    title = str(job.get("title") or "").strip()
    apply_link = str(job.get("applyUrl") or job.get("jobUrl") or "").strip()
    if not title or not apply_link:
        return None

    return {
        "Company": company,
        "Title": title,
        "Location": str(job.get("location") or "Unknown").strip() or "Unknown",
        "Job Description": clean_job_description(
            str(job.get("descriptionPlain") or "")
        ),
        "Apply Link": apply_link,
    }


def scrape_ashby_jobs(
    companies: Iterable[str] = ASHBY_COMPANIES,
) -> pd.DataFrame:
    """Fetch Ashby boards and return unfiltered normalized job postings."""
    results: list[dict] = []

    for company in companies:
        print(f"正在获取 {company} 的 Ashby 职位……")
        url = ASHBY_JOB_BOARD_URL.format(company=company)

        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            payload = response.json()
            jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
            if not isinstance(jobs, list):
                raise ValueError("Ashby response jobs must be a JSON list")
        except (requests.RequestException, ValueError) as error:
            print(f"{company} Ashby 获取失败：{error}")
            print("-" * 50)
            continue

        normalized_jobs = [
            normalized
            for job in jobs
            if (normalized := normalize_ashby_job(company, job)) is not None
        ]
        results.extend(normalized_jobs)
        print(f"{company} Ashby 获取成功，职位数：{len(normalized_jobs)}")
        print("-" * 50)

    return pd.DataFrame(results, columns=SCRAPED_JOB_COLUMNS)
