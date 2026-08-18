"""Lever Postings API scraper using the shared job filtering rules."""

from collections.abc import Iterable

import pandas as pd
import requests

from src.config import LEVER_COMPANIES
from src.filters.location_filter import is_excluded_location
from src.scrapers.greenhouse import (
    SCRAPED_JOB_COLUMNS,
    clean_job_description,
    title_has_excluded_keyword,
    title_has_target_keyword,
)


def _combine_job_description(job: dict) -> str:
    """Combine Lever's plain-text and structured description sections."""
    parts: list[str] = []

    description = job.get("descriptionPlain", "")
    if description:
        parts.append(str(description))

    for section in job.get("lists") or []:
        if not isinstance(section, dict):
            continue
        heading = section.get("text", "")
        heading_text = str(heading).strip() if heading else ""
        content = clean_job_description(str(section.get("content", "")))
        section_text = " ".join(
            value for value in (heading_text, content) if value
        )
        if section_text:
            parts.append(section_text)

    additional = job.get("additionalPlain", "")
    if additional:
        parts.append(str(additional))

    return clean_job_description("\n".join(parts))


def scrape_lever_jobs(
    companies: Iterable[str] = LEVER_COMPANIES,
) -> pd.DataFrame:
    """Fetch and filter Lever jobs using the shared normalized schema."""
    results: list[dict] = []
    total_jobs = 0
    title_relevant_jobs = 0
    after_title_exclusions = 0
    after_location_filter = 0

    for company in companies:
        url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        print(f"正在获取 Lever {company} 的职位……")

        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            jobs = response.json()
            if not isinstance(jobs, list):
                raise ValueError("Lever response must be a JSON list")
        except (requests.RequestException, ValueError) as error:
            print(f"Lever {company} 请求失败：{error}")
            print("-" * 50)
            continue

        total_jobs += len(jobs)
        print(f"Lever {company} 获取成功，职位数：{len(jobs)}")

        for job in jobs:
            if not isinstance(job, dict):
                continue

            title = str(job.get("text", "")).strip()
            if not title_has_target_keyword(title):
                continue
            title_relevant_jobs += 1

            if title_has_excluded_keyword(title):
                continue
            after_title_exclusions += 1

            categories = job.get("categories") or {}
            if not isinstance(categories, dict):
                categories = {}
            location = str(categories.get("location", "Unknown")).strip()
            if is_excluded_location(location):
                continue
            after_location_filter += 1

            job_description = _combine_job_description(job)
            if not job_description:
                continue

            results.append(
                {
                    "Company": company,
                    "Title": title,
                    "Location": location,
                    "Job Description": job_description,
                    "Apply Link": job.get("applyUrl")
                    or job.get("hostedUrl", ""),
                }
            )

        print("-" * 50)

    dataframe = pd.DataFrame(results, columns=SCRAPED_JOB_COLUMNS)
    print(f"Lever raw jobs fetched: {total_jobs}")
    print(f"Lever title-relevant jobs: {title_relevant_jobs}")
    print(
        "Lever after seniority/unrelated exclusions: "
        f"{after_title_exclusions}"
    )
    print(f"Lever after location filtering: {after_location_filter}")
    print(f"Lever jobs with complete descriptions: {len(dataframe)}")
    return dataframe
