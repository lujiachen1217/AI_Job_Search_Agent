import csv
import re
from pathlib import Path

import pandas as pd

from src.matchers.skill_aliases import canonicalize_skill, extract_alias_skills


MATCHED_JOB_COLUMNS = [
    "Company",
    "Title",
    "Location",
    "Minimum Experience Years",
    "Experience Level",
    "Experience Evidence",
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
    """用技能库和受控别名识别 canonical 技能。"""
    found_skills = extract_alias_skills(text)
    for skill in skill_list:
        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
        if re.search(pattern, text, flags=re.IGNORECASE):
            found_skills.add(canonicalize_skill(skill))
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


def _print_skill_match_audit(
    job: dict,
    resume_skills: set[str],
    match_result: dict,
) -> None:
    """Print detailed diagnostics using the actual keyword-match result."""
    score = match_result["match_score"]
    if score >= 50:
        ranking_signal = "High"
    elif score >= 20:
        ranking_signal = "Medium"
    else:
        ranking_signal = "Low"

    print("-" * 50)
    print("Skill Match Audit")
    print(f"\nCompany: {job['Company']}")
    print(f"Title: {job['Title']}")
    print(f"Location: {job['Location']}")
    print(f"\nMinimum Experience Years: {job['Minimum Experience Years']}")
    print(f"Experience Level: {job['Experience Level']}")
    print(f"\nResume Skills Recognized:\n{sorted(resume_skills)}")
    print(f"\nJD Skills Recognized:\n{sorted(match_result['job_skills'])}")
    print(f"\nMatched Skills:\n{sorted(match_result['matched_skills'])}")
    print(f"\nMissing JD Skills:\n{sorted(match_result['missing_skills'])}")
    print(f"\nSkill Match Score:\n{score}%")
    print(f"\nRanking Signal:\n{ranking_signal}")
    print("\nRetained for AI Ranking:\nYes")
    print("-" * 50)


def rank_matching_jobs(
    jobs_dataframe: pd.DataFrame,
    resume_skills: set[str],
    skill_list: list[str],
    debug: bool = False,
) -> pd.DataFrame:
    """Calculate soft skill signals and rank every hard-filtered candidate."""
    results: list[dict] = []
    jobs_with_recognized_skills = 0

    for job in jobs_dataframe.to_dict(orient="records"):
        match_result = calculate_keyword_match(
            resume_skills=resume_skills,
            job_description=job["Job Description"],
            skill_list=skill_list,
        )
        if match_result["job_skills"]:
            jobs_with_recognized_skills += 1
        if debug:
            _print_skill_match_audit(
                job=job,
                resume_skills=resume_skills,
                match_result=match_result,
            )

        results.append(
            {
                "Company": job["Company"],
                "Title": job["Title"],
                "Location": job["Location"],
                "Minimum Experience Years": job["Minimum Experience Years"],
                "Experience Level": job["Experience Level"],
                "Experience Evidence": job["Experience Evidence"],
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
            f"候选岗位：{job['Title']} | Location：{job['Location']} | "
            f"Skill Match Score：{match_result['match_score']}%"
        )

    dataframe = pd.DataFrame(results, columns=MATCHED_JOB_COLUMNS)
    if not dataframe.empty:
        dataframe = dataframe.sort_values(
            by="Match Score", ascending=False, kind="stable"
        ).reset_index(drop=True)

    print(f"Candidate jobs after hard filters: {len(jobs_dataframe)}")
    print(
        "Candidate jobs with recognized JD skills: "
        f"{jobs_with_recognized_skills}"
    )
    print(f"Jobs ranked for AI evaluation: {len(dataframe)}")
    return dataframe
