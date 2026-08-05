import csv
import re
from pathlib import Path

import pandas as pd


MATCHED_JOB_COLUMNS = [
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


def load_skill_list(csv_path: str | Path) -> list[str]:
    """读取技能库，去除空值和重复项，同时保留原始顺序。"""
    skills: list[str] = []
    seen: set[str] = set()

    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if "skill" not in (reader.fieldnames or []):
            raise ValueError("skills.csv 必须包含名为 'skill' 的列。")

        for row in reader:
            skill = row.get("skill", "").strip()
            normalized_skill = skill.casefold()
            if skill and normalized_skill not in seen:
                skills.append(skill)
                seen.add(normalized_skill)

    return skills


def extract_skills(text: str, skill_list: list[str]) -> set[str]:
    """用技能库进行精确关键词识别。"""
    found_skills: set[str] = set()
    for skill in skill_list:
        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
        if re.search(pattern, text, flags=re.IGNORECASE):
            found_skills.add(skill)
    return found_skills


def calculate_keyword_match(
    resume_skills: set[str],
    job_description: str,
    skill_list: list[str],
) -> dict:
    """按原有算法计算简历与职位的关键词技能匹配结果。"""
    job_skills = extract_skills(job_description, skill_list)
    matched_skills = resume_skills & job_skills
    missing_skills = job_skills - resume_skills

    score = 0.0
    if job_skills:
        score = len(matched_skills) / len(job_skills) * 100

    return {
        "job_skills": job_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "match_score": round(score, 1),
    }


def rank_matching_jobs(
    jobs_dataframe: pd.DataFrame,
    resume_skills: set[str],
    skill_list: list[str],
    minimum_match_score: float,
) -> pd.DataFrame:
    """计算职位分数，按最低分过滤，并按 Match Score 降序排列。"""
    results: list[dict] = []

    for job in jobs_dataframe.to_dict(orient="records"):
        match_result = calculate_keyword_match(
            resume_skills=resume_skills,
            job_description=job["Job Description"],
            skill_list=skill_list,
        )
        if match_result["match_score"] < minimum_match_score:
            continue

        results.append(
            {
                "Company": job["Company"],
                "Title": job["Title"],
                "Location": job["Location"],
                "Match Score": match_result["match_score"],
                "Job Skills": ", ".join(sorted(match_result["job_skills"])),
                "Matched Skills": ", ".join(
                    sorted(match_result["matched_skills"])
                ),
                "Missing Skills": ", ".join(
                    sorted(match_result["missing_skills"])
                ),
                "Job Description": job["Job Description"],
                "Apply Link": job["Apply Link"],
            }
        )
        print(
            f"保留岗位：{job['Title']} | Location：{job['Location']} | "
            f"Match Score：{match_result['match_score']}%"
        )

    dataframe = pd.DataFrame(results, columns=MATCHED_JOB_COLUMNS)
    if not dataframe.empty:
        dataframe = dataframe.sort_values(
            by="Match Score", ascending=False
        ).reset_index(drop=True)

    print(f"匹配职位数：{len(dataframe)}")
    return dataframe
