import csv

from job_scraper import save_jobs_to_excel, scrape_jobs
from match_score import calculate_ai_match, extract_skills
from resume_analyzer import analyze_resume
from resume_parser import extract_text_from_pdf


RESUME_PATH = "data/resume.pdf"
SKILLS_PATH = "data/skills.csv"
OUTPUT_PATH = "jobs.xlsx"


def load_skill_list(csv_path: str) -> list[str]:
    """读取技能库，去除空值和重复项，同时保留原始顺序。"""
    skills: list[str] = []
    seen: set[str] = set()

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
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


def print_job_summary(dataframe) -> None:
    """在 Terminal 中展示较短的岗位汇总。"""
    if dataframe.empty:
        print("没有找到符合条件的职位。")
        return

    summary_columns = [
        "Company",
        "Title",
        "Location",
        "Match Score",
        "AI Match Score",
        "Recommendation",
        "Matched Skills",
        "Missing Skills",
    ]

    # 只展示实际存在的列，避免某些情况下报错
    available_columns = [
        column
        for column in summary_columns
        if column in dataframe.columns
    ]

    print(dataframe[available_columns].to_string(index=False))


def add_ai_match_scores(
    jobs_dataframe,
    resume_data: dict,
    top_n: int = 5,
):
    """
    只对关键词分数最高的前 top_n 个岗位进行 GPT 分析。

    这样可以控制 API 调用次数和费用。
    """
    jobs_dataframe = jobs_dataframe.copy()
    jobs_dataframe = jobs_dataframe.reset_index(drop=True)

    jobs_dataframe["AI Match Score"] = None
    jobs_dataframe["Recommendation"] = ""
    jobs_dataframe["AI Matched Qualifications"] = ""
    jobs_dataframe["AI Missing Qualifications"] = ""
    jobs_dataframe["AI Reasoning"] = ""

    number_to_analyze = min(top_n, len(jobs_dataframe))

    for index in range(number_to_analyze):
        row = jobs_dataframe.iloc[index]

        print(
            f"\n正在进行 AI 匹配："
            f"{row['Company']} - {row['Title']}"
        )

        try:
            ai_result = calculate_ai_match(
                resume_data=resume_data,
                job_title=row["Title"],
                job_description=row["Job Description"],
            )

            jobs_dataframe.at[index, "AI Match Score"] = (
                ai_result.get("ai_match_score")
            )

            jobs_dataframe.at[index, "Recommendation"] = (
                ai_result.get("recommendation", "")
            )

            jobs_dataframe.at[
                index, "AI Matched Qualifications"
            ] = ", ".join(
                ai_result.get("matched_qualifications", [])
            )

            jobs_dataframe.at[
                index, "AI Missing Qualifications"
            ] = ", ".join(
                ai_result.get("missing_qualifications", [])
            )

            jobs_dataframe.at[index, "AI Reasoning"] = " | ".join(
                ai_result.get("reasoning", [])
            )

            print(
                f"AI Score：{ai_result.get('ai_match_score')} | "
                f"Recommendation："
                f"{ai_result.get('recommendation', '')}"
            )

        except Exception as error:
            print(f"AI 匹配失败：{error}")

    return jobs_dataframe


def main() -> None:
    print("正在读取技能库……")
    skill_list = load_skill_list(SKILLS_PATH)
    print(f"技能库数量：{len(skill_list)}")

    print("\n正在读取简历……")
    resume_text = extract_text_from_pdf(RESUME_PATH)

    print("正在识别简历技能……")
    resume_skills = extract_skills(
        resume_text,
        skill_list,
    )

    print(f"简历技能数量：{len(resume_skills)}")
    print(
        "简历技能：",
        ", ".join(sorted(resume_skills)),
    )

    print("\n正在使用 GPT 分析简历……")
    resume_data = analyze_resume(resume_text)

    print("\n正在抓取并进行关键词匹配……")
    jobs_dataframe = scrape_jobs(
        resume_skills=resume_skills,
        skill_list=skill_list,
    )

    if jobs_dataframe.empty:
        print("\n没有找到符合条件的岗位。")
        return

    print("\n正在对 Top 5 岗位进行 AI 语义匹配……")
    jobs_dataframe = add_ai_match_scores(
        jobs_dataframe=jobs_dataframe,
        resume_data=resume_data,
        top_n=5,
    )

    print("\n岗位汇总：")
    print_job_summary(jobs_dataframe)

    save_jobs_to_excel(
        jobs_dataframe,
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()