import pandas as pd

from src.analyzers.resume_analyzer import analyze_resume
from src.config import (
    EXCEL_OUTPUT_PATH,
    GREENHOUSE_COMPANIES,
    MINIMUM_MATCH_SCORE,
    RESUME_PATH,
    SKILLS_PATH,
    TOP_AI_MATCH_COUNT,
)
from src.exporters.excel_exporter import save_jobs_to_excel
from src.matchers.ai_matcher import add_ai_match_scores
from src.matchers.skill_matcher import (
    extract_skills,
    load_skill_list,
    rank_matching_jobs,
)
from src.parsers.resume_parser import extract_text_from_pdf
from src.scrapers.greenhouse import scrape_jobs


def print_job_summary(dataframe: pd.DataFrame) -> None:
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
        "Final Match Score",
        "Recommendation",
        "Matched Skills",
        "Missing Skills",
    ]
    available_columns = [
        column for column in summary_columns if column in dataframe.columns
    ]
    print(dataframe[available_columns].to_string(index=False))


def main() -> None:
    """运行职位搜索、匹配、展示和导出 Pipeline。"""
    print("正在读取技能库……")
    skill_list = load_skill_list(SKILLS_PATH)
    print(f"技能库数量：{len(skill_list)}")

    print("\n正在读取简历……")
    resume_text = extract_text_from_pdf(RESUME_PATH)

    print("正在识别简历技能……")
    resume_skills = extract_skills(resume_text, skill_list)
    print(f"简历技能数量：{len(resume_skills)}")
    print("简历技能：", ", ".join(sorted(resume_skills)))

    print("\n正在使用 GPT 分析简历……")
    resume_data = analyze_resume(resume_text)

    print("\n正在抓取并进行关键词匹配……")
    jobs_dataframe = scrape_jobs(companies=GREENHOUSE_COMPANIES)
    jobs_dataframe = rank_matching_jobs(
        jobs_dataframe=jobs_dataframe,
        resume_skills=resume_skills,
        skill_list=skill_list,
        minimum_match_score=MINIMUM_MATCH_SCORE,
    )

    if jobs_dataframe.empty:
        print("\n没有找到符合条件的岗位。")
        return

    print("\n正在对 Top 5 岗位进行 AI 语义匹配……")
    jobs_dataframe = add_ai_match_scores(
        jobs_dataframe=jobs_dataframe,
        resume_data=resume_data,
        top_n=TOP_AI_MATCH_COUNT,
    )

    print("\n岗位汇总：")
    print_job_summary(jobs_dataframe)
    save_jobs_to_excel(jobs_dataframe, EXCEL_OUTPUT_PATH)


if __name__ == "__main__":
    main()
