"""Cover letter strategy selection."""

import json
import math
from numbers import Real

import pandas as pd

from src.clients.openai_client import get_openai_client


def choose_cover_letter_type(final_score: float) -> str:
    """Choose a cover letter strategy based on the final match score."""
    if final_score >= 80:
        return "custom"
    if final_score >= 65:
        return "standard"
    if final_score >= 50:
        return "template"
    return "skip"


def generate_template_cover_letter(
    company: str,
    job_title: str,
    matched_skills: str,
) -> str:
    """Create a concise cover letter from known job-match details."""
    return f"""Dear Hiring Team at {company},

I am writing to express my interest in the {job_title} position at {company}. My relevant skills include {matched_skills}, and I would welcome the opportunity to apply them while contributing to your team.

Thank you for considering my application. I would be glad to discuss how my skills align with this role.

Sincerely,
Applicant"""


def generate_standard_cover_letter(
    resume_data: dict,
    company: str,
    job_title: str,
    job_description: str,
    matched_skills: str,
) -> str:
    """Generate a concise, resume-grounded cover letter with GPT."""
    prompt = f"""
Write a concise, professional cover letter for the position below.

Tailor the letter to the role and emphasize the candidate's most relevant
qualifications. Use the matched skills as supporting context and avoid generic
filler. Do not invent or infer any experience, education, achievement, skill,
or qualification that is not explicitly supported by the resume data.

Return only the cover letter text, with no heading, notes, or commentary.

Candidate resume data:
{json.dumps(resume_data, ensure_ascii=False)}

Company:
{company}

Job title:
{job_title}

Job description:
{job_description}

Matched skills:
{matched_skills}
"""
    response = get_openai_client().responses.create(
        model="gpt-5",
        input=prompt,
    )
    return response.output_text.strip()


def generate_custom_cover_letter(
    resume_data: dict,
    company: str,
    job_title: str,
    job_description: str,
    matched_qualifications: str,
    missing_qualifications: str,
    reasoning: str,
) -> str:
    """Generate a highly tailored cover letter using prior AI match analysis."""
    prompt = f"""
Write a highly tailored, professional cover letter for the position below.

Use the candidate's resume and the previous job-match analysis to identify
the strongest evidence for why the candidate fits this specific role.

Prioritize:
1. The most relevant qualifications and experiences.
2. Concrete evidence from the resume.
3. Why the candidate's background aligns with the responsibilities of the role.
4. A natural explanation of transferable strengths where appropriate.

Be aware of the listed missing qualifications, but do not fabricate experience
to compensate for them. Do not mention missing qualifications unnecessarily
unless they can be addressed naturally through transferable experience.

Do not invent or infer any experience, education, achievement, skill,
or qualification that is not explicitly supported by the resume data.

Keep the letter concise and specific. Avoid generic filler.

Return only the cover letter text, with no heading, notes, or commentary.

Candidate resume data:
{json.dumps(resume_data, ensure_ascii=False)}

Company:
{company}

Job title:
{job_title}

Job description:
{job_description}

Matched qualifications:
{matched_qualifications}

Missing qualifications:
{missing_qualifications}

Previous AI match reasoning:
{reasoning}
"""
    response = get_openai_client().responses.create(
        model="gpt-5",
        input=prompt,
    )
    return response.output_text.strip()


def add_cover_letters(
    jobs_dataframe: pd.DataFrame,
    resume_data: dict,
) -> pd.DataFrame:
    """Add cover letter strategies and content for jobs with final scores."""
    jobs_dataframe = jobs_dataframe.copy()
    jobs_dataframe["Cover Letter Type"] = ""
    jobs_dataframe["Cover Letter"] = ""

    for index, row in jobs_dataframe.iterrows():
        final_score = row["Final Match Score"]
        if (
            isinstance(final_score, bool)
            or not isinstance(final_score, Real)
            or not math.isfinite(float(final_score))
        ):
            continue

        cover_letter_type = choose_cover_letter_type(float(final_score))
        jobs_dataframe.at[index, "Cover Letter Type"] = cover_letter_type

        if cover_letter_type == "template":
            jobs_dataframe.at[index, "Cover Letter"] = (
                generate_template_cover_letter(
                    company=row["Company"],
                    job_title=row["Title"],
                    matched_skills=row["Matched Skills"],
                )
            )
        elif cover_letter_type == "standard":
            try:
                jobs_dataframe.at[index, "Cover Letter"] = (
                    generate_standard_cover_letter(
                        resume_data=resume_data,
                        company=row["Company"],
                        job_title=row["Title"],
                        job_description=row["Job Description"],
                        matched_skills=row["Matched Skills"],
                    )
                )
            except Exception as error:
                print(
                    "Standard cover letter generation failed for "
                    f"{row['Company']} - {row['Title']}: {error}"
                )
        elif cover_letter_type == "custom":
            try:
                jobs_dataframe.at[index, "Cover Letter"] = (
                    generate_custom_cover_letter(
                        resume_data=resume_data,
                        company=row["Company"],
                        job_title=row["Title"],
                        job_description=row["Job Description"],
                        matched_qualifications=row[
                            "AI Matched Qualifications"
                        ],
                        missing_qualifications=row[
                            "AI Missing Qualifications"
                        ],
                        reasoning=row["AI Reasoning"],
                    )
                )
            except Exception as error:
                print(
                    "Custom cover letter generation failed for "
                    f"{row['Company']} - {row['Title']}: {error}"
                )

    return jobs_dataframe
