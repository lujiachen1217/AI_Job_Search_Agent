import json

from src.clients.openai_client import get_openai_client


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
    response = get_openai_client().responses.create(model="gpt-5", input=prompt)
    return json.loads(response.output_text)
