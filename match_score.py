import json
import re



def extract_skills(text: str, skill_list: list[str]) -> set[str]:
    """用技能库进行精确关键词识别。"""
    found_skills = set()

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
    """传统关键词匹配，适合快速批量筛选岗位。"""
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


def calculate_ai_match(
    resume_data: dict,
    job_title: str,
    job_description: str,
) -> dict:
    """
    使用 GPT 对简历和职位进行语义匹配。

    不只比较完全相同的技能名称，也会判断：
    1. 技能之间是否相关
    2. 教育和项目背景是否满足要求
    3. 岗位经验级别是否适合候选人
    """

    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
    client = OpenAI()

    prompt = f"""
You are an experienced technical recruiter evaluating an early-career
candidate for a job.

Evaluate the candidate against the job description using semantic matching.
Do not rely only on exact keyword matches.

Consider:

1. Technical skills
2. Statistical and analytical knowledge
3. Education
4. Relevant work and project experience
5. Required years of experience
6. Seniority level
7. Industry relevance

Scoring guide:

90-100:
The candidate meets nearly all major requirements.

75-89:
The candidate is a strong match but has a few manageable gaps.

60-74:
The candidate is a reasonable match and may be worth applying.

40-59:
The candidate has some relevant qualifications but has major gaps.

0-39:
The candidate is not currently a strong match.

Return ONLY valid JSON using exactly this structure:

{{
  "ai_match_score": 0,
  "recommendation": "",
  "matched_qualifications": [],
  "missing_qualifications": [],
  "reasoning": []
}}

The recommendation must be exactly one of:

75-100: "Strong Apply"
60-74: "Apply"
45-59: "Maybe"
0-44: "Do Not Apply"

Candidate resume:

{json.dumps(resume_data, ensure_ascii=False)}

Job title:

{job_title}

Job description:

{job_description}
"""

    response = client.responses.create(
        model="gpt-5",
        input=prompt,
    )

    return json.loads(response.output_text)