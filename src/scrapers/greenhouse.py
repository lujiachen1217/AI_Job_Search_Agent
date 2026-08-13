import html
import re
from collections.abc import Iterable

import pandas as pd
import requests

from src.config import (
    EXCLUDED_JOB_KEYWORDS,
    EXCLUDED_LOCATION_KEYWORDS,
    GREENHOUSE_COMPANIES,
    TARGET_JOB_KEYWORDS,
)


SCRAPED_JOB_COLUMNS = [
    "Company",
    "Title",
    "Location",
    "Job Description",
    "Apply Link",
]


def is_excluded_location(
    location: str,
    excluded_keywords: Iterable[str] = EXCLUDED_LOCATION_KEYWORDS,
) -> bool:
    """判断岗位地点是否属于当前不考虑的国家或城市。"""
    location_lower = location.casefold().strip()
    has_excluded_location = any(
        keyword.casefold() in location_lower for keyword in excluded_keywords
    )
    is_uk_location = bool(re.search(r"\buk\b", location_lower))
    return has_excluded_location or is_uk_location


def clean_job_description(raw_description: str) -> str:
    """把 Greenhouse 返回的 HTML 职位描述转换成普通文本。"""
    text = html.unescape(raw_description or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_job_description(company: str, job_id: int) -> str:
    """获取 Greenhouse 中单个职位的完整 JD。"""
    detail_url = (
        f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}"
    )
    try:
        response = requests.get(detail_url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"职位详情请求失败：{error}")
        return ""

    raw_description = response.json().get("content", "")
    return clean_job_description(raw_description)


def title_is_relevant(
    title: str,
    target_keywords: Iterable[str] = TARGET_JOB_KEYWORDS,
    exclude_keywords: Iterable[str] = EXCLUDED_JOB_KEYWORDS,
) -> bool:
    """判断职位标题是否属于目标岗位，并排除高级或不相关岗位。"""
    return title_has_target_keyword(title, target_keywords) and not (
        title_has_excluded_keyword(title, exclude_keywords)
    )


def _contains_title_phrase(title: str, phrase: str) -> bool:
    """Match a title phrase without treating it as part of a larger word."""
    pattern = r"(?<!\w)" + re.escape(phrase.casefold()) + r"(?!\w)"
    return bool(re.search(pattern, title.casefold()))


def title_has_target_keyword(
    title: str,
    target_keywords: Iterable[str] = TARGET_JOB_KEYWORDS,
) -> bool:
    """Return whether a title contains one of the configured target phrases."""
    return any(
        _contains_title_phrase(title, keyword) for keyword in target_keywords
    )


def title_has_excluded_keyword(
    title: str,
    exclude_keywords: Iterable[str] = EXCLUDED_JOB_KEYWORDS,
) -> bool:
    """Return whether a title contains a configured exclusion phrase."""
    return any(
        _contains_title_phrase(title, keyword) for keyword in exclude_keywords
    )


def scrape_jobs(
    companies: Iterable[str] = GREENHOUSE_COMPANIES,
) -> pd.DataFrame:
    """抓取并筛选 Greenhouse 职位，返回包含完整 JD 的 DataFrame。"""
    results: list[dict] = []
    total_jobs = 0
    title_relevant_jobs = 0
    after_title_exclusions = 0
    after_location_filter = 0

    for company in companies:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
        print(f"正在获取 {company} 的职位……")

        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as error:
            print(f"{company} 请求失败：{error}")
            print("-" * 50)
            continue

        jobs = response.json().get("jobs", [])
        total_jobs += len(jobs)
        print(f"{company} 获取成功，职位数：{len(jobs)}")

        for job in jobs:
            title = job.get("title", "").strip()
            if not title_has_target_keyword(title):
                continue
            title_relevant_jobs += 1

            if title_has_excluded_keyword(title):
                continue
            after_title_exclusions += 1

            location = job.get("location", {}).get("name", "Unknown").strip()
            if is_excluded_location(location):
                continue
            after_location_filter += 1

            job_id = job.get("id")
            if not job_id:
                continue

            job_description = get_job_description(company=company, job_id=job_id)
            if not job_description:
                continue

            results.append(
                {
                    "Company": company,
                    "Title": title,
                    "Location": location,
                    "Job Description": job_description,
                    "Apply Link": job.get("absolute_url", ""),
                }
            )

        print("-" * 50)

    dataframe = pd.DataFrame(results, columns=SCRAPED_JOB_COLUMNS)
    print(f"Raw jobs fetched: {total_jobs}")
    print(f"Title-relevant jobs: {title_relevant_jobs}")
    print(f"After seniority/unrelated exclusions: {after_title_exclusions}")
    print(f"After location filtering: {after_location_filter}")
    print(f"Jobs with complete descriptions: {len(dataframe)}")
    return dataframe
