import html
import re
from typing import Iterable

import pandas as pd
import requests

from match_score import calculate_keyword_match


MINIMUM_MATCH_SCORE = 20


COMPANIES = [
    "xai",
    "scaleai",
    "datadog",
    "figma",
    "plaid",
    "reddit",
    "discord",
    "affirm",
]


TARGET_KEYWORDS = [
    "data analyst",
    "data scientist",
    "business analyst",
    "product analyst",
    "biostatistician",
    "biostatistics",
    "health data",
    "health analytics",
    "clinical data",
    "machine learning engineer",
    "research engineer",
]


EXCLUDE_KEYWORDS = [
    "senior",
    "staff",
    "principal",
    "director",
    "manager",
    "lead",
    "head of",
    "vice president",
    "chief",
    "tutor",
    "account executive",
    "sales",
    "marketing",
    "recruiter",
    "research scientist",
    "phd",
    "postdoc",
    "postdoctoral",
]


EXCLUDED_LOCATION_KEYWORDS = [
    "paris",
    "france",
    "london",
    "united kingdom",
    "canada",
    "doha",
    "qatar",
]


OUTPUT_COLUMNS = [
    "Company",
    "Title",
    "Location",
    "Match Score",
    "Job Skills",
    "Matched Skills",
    "Missing Skills",
    "Job Description",
    "Apply Link",
]


def is_excluded_location(location: str) -> bool:
    """
    判断岗位地点是否属于当前不考虑的国家或城市。

    对 UK 使用单独的完整单词判断，避免短字符串误匹配。
    """
    location_lower = location.casefold().strip()

    has_excluded_location = any(
        keyword.casefold() in location_lower
        for keyword in EXCLUDED_LOCATION_KEYWORDS
    )

    is_uk_location = bool(
        re.search(r"\buk\b", location_lower)
    )

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
        f"https://boards-api.greenhouse.io/"
        f"v1/boards/{company}/jobs/{job_id}"
    )

    try:
        response = requests.get(
            detail_url,
            timeout=15,
        )
        response.raise_for_status()

    except requests.RequestException as error:
        print(f"职位详情请求失败：{error}")
        return ""

    raw_description = response.json().get(
        "content",
        "",
    )

    return clean_job_description(raw_description)


def title_is_relevant(
    title: str,
    target_keywords: Iterable[str] = TARGET_KEYWORDS,
    exclude_keywords: Iterable[str] = EXCLUDE_KEYWORDS,
) -> bool:
    """判断职位标题是否属于目标岗位，并排除高级或不相关岗位。"""
    title_lower = title.casefold()

    has_target_keyword = any(
        keyword.casefold() in title_lower
        for keyword in target_keywords
    )

    has_excluded_keyword = any(
        keyword.casefold() in title_lower
        for keyword in exclude_keywords
    )

    return has_target_keyword and not has_excluded_keyword


def scrape_jobs(
    resume_skills: set[str],
    skill_list: list[str],
    companies: Iterable[str] = COMPANIES,
) -> pd.DataFrame:
    """抓取目标公司岗位，完成关键词匹配，并返回排序后的 DataFrame。"""
    results: list[dict] = []
    total_jobs = 0

    for company in companies:
        url = (
            f"https://boards-api.greenhouse.io/"
            f"v1/boards/{company}/jobs"
        )

        print(f"正在获取 {company} 的职位……")

        try:
            response = requests.get(
                url,
                timeout=15,
            )
            response.raise_for_status()

        except requests.RequestException as error:
            print(f"{company} 请求失败：{error}")
            print("-" * 50)
            continue

        jobs = response.json().get("jobs", [])
        total_jobs += len(jobs)

        print(
            f"{company} 获取成功，"
            f"职位数：{len(jobs)}"
        )

        for job in jobs:
            title = job.get("title", "").strip()

            # 第一层筛选：岗位标题
            if not title_is_relevant(title):
                continue

            location = (
                job.get("location", {})
                .get("name", "Unknown")
                .strip()
            )

            # 第二层筛选：岗位地点
            if is_excluded_location(location):
                continue

            job_id = job.get("id")

            if not job_id:
                continue

            # 标题和地点通过以后，再请求完整 JD
            job_description = get_job_description(
                company=company,
                job_id=job_id,
            )

            if not job_description:
                continue

            match_result = calculate_keyword_match(
                resume_skills=resume_skills,
                job_description=job_description,
                skill_list=skill_list,
            )

            # 第三层筛选：最低关键词匹配分数
            if (
                match_result["match_score"]
                < MINIMUM_MATCH_SCORE
            ):
                continue

            results.append(
                {
                    "Company": company,
                    "Title": title,
                    "Location": location,
                    "Match Score": match_result[
                        "match_score"
                    ],
                    "Job Skills": ", ".join(
                        sorted(
                            match_result["job_skills"]
                        )
                    ),
                    "Matched Skills": ", ".join(
                        sorted(
                            match_result[
                                "matched_skills"
                            ]
                        )
                    ),
                    "Missing Skills": ", ".join(
                        sorted(
                            match_result[
                                "missing_skills"
                            ]
                        )
                    ),
                    "Job Description": job_description,
                    "Apply Link": job.get(
                        "absolute_url",
                        "",
                    ),
                }
            )

            print(
                f"保留岗位：{title} | "
                f"Location：{location} | "
                f"Match Score："
                f"{match_result['match_score']}%"
            )

        print("-" * 50)

    dataframe = pd.DataFrame(
        results,
        columns=OUTPUT_COLUMNS,
    )

    if not dataframe.empty:
        dataframe = (
            dataframe.sort_values(
                by="Match Score",
                ascending=False,
            )
            .reset_index(drop=True)
        )

    print(f"成功获取的职位总数：{total_jobs}")
    print(f"匹配职位数：{len(dataframe)}")

    return dataframe


def save_jobs_to_excel(
    dataframe: pd.DataFrame,
    output_path: str = "jobs.xlsx",
) -> None:
    """把岗位结果保存为 Excel。"""
    dataframe.to_excel(
        output_path,
        index=False,
    )

    print(f"✅ Excel 已生成：{output_path}")


if __name__ == "__main__":
    print("请运行 main.py 启动完整流程。")