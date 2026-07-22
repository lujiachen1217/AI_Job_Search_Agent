import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

prompt = """
You are a senior recruiter.

Introduce yourself in one short paragraph.

Then list exactly three recruiter responsibilities.

Return ONLY valid JSON using this structure:

{
  "introduction": "",
  "responsibilities": [
    "",
    "",
    ""
  ]
}
"""

response = client.responses.create(
    model="gpt-5",
    input=prompt,
)

result_text = response.output_text
result = json.loads(result_text)

print("Introduction:")
print(result["introduction"])

print("\nResponsibilities:")
for responsibility in result["responsibilities"]:
    print("-", responsibility)