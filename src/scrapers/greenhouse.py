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
    title_lower = title.casefold()
    has_target_keyword = any(
        keyword.casefold() in title_lower for keyword in target_keywords
    )
    has_excluded_keyword = any(
        keyword.casefold() in title_lower for keyword in exclude_keywords
    )
    return has_target_keyword and not has_excluded_keyword


def scrape_jobs(
    companies: Iterable[str] = GREENHOUSE_COMPANIES,
) -> pd.DataFrame:
    """抓取并筛选 Greenhouse 职位，返回包含完整 JD 的 DataFrame。"""
    results: list[dict] = []
    total_jobs = 0

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
            if not title_is_relevant(title):
                continue

            location = job.get("location", {}).get("name", "Unknown").strip()
            if is_excluded_location(location):
                continue

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
    print(f"成功获取的职位总数：{total_jobs}")
    return dataframe
