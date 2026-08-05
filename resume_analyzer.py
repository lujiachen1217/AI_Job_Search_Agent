import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()


def analyze_resume(resume_text: str) -> dict:
    """使用 GPT 把简历文本转换成结构化 Python 字典。"""
    prompt = f"""
You are an experienced recruiter.

Extract information from the resume.
Return ONLY valid JSON in exactly this structure:

{{
  "name": "",
  "education": "",
  "skills": [],
  "experience": [
    {{
      "company": "",
      "title": "",
      "dates": "",
      "details": []
    }}
  ]
}}

Resume:
{resume_text}
"""

    response = client.responses.create(
        model="gpt-5",
        input=prompt,
    )

    return json.loads(response.output_text)
