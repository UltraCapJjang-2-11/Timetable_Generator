import openai
import json
from django.conf import settings

# 실제 API 키는 settings 또는 환경변수를 통해 관리하세요.
openai.api_key = settings.OPENAI_API_KEY

def extract_graduation_info_from_text(pdf_text: str) -> dict:
    """
    GPT API를 사용해 PDF 텍스트에서 졸업 이수 정보를 추출합니다.
    아래 필드들을 오직 순수 JSON 형식으로 출력하도록 요청합니다:
      - user_student_id (string)
      - user_name (string)
      - user_major (string)
      - user_year (string)       # 예: "3학년"
      - total_credits (integer)
      - major_credits (integer)
      - general_credits (integer)
      - free_credits (integer)
      - total_requirement (integer)
      - major_requirement (integer)
      - general_requirement (integer)
      - free_requirement (integer)
      - missing_subjects (array of objects; 각 객체는 "type"과 "description"을 포함)
      - completed_courses (array of strings; 이수한 과목 코드 목록)
    """
    system_prompt = (
        "You are a helpful assistant specialized in extracting graduation information from academic documents. "
        "When given PDF text, extract the following fields and output ONLY valid JSON with no extra text: "
        "user_student_id, user_name, user_major, user_year, total_credits, major_credits, general_credits, free_credits, "
        "total_requirement, major_requirement, general_requirement, free_requirement, missing_subjects, completed_courses."
    )
    user_prompt = f"""
Below is the extracted text from a graduation requirements PDF.
Please extract the following fields from the text and output ONLY valid JSON (without any additional text):
- user_student_id (string)
- user_name (string)
- user_major (string)
- user_year (string)       # e.g. "3학년"
- total_credits (integer)
- major_credits (integer)
- general_credits (integer)
- free_credits (integer)
- total_requirement (integer)    # graduation requirement for total credits
- major_requirement (integer)      # graduation requirement for major credits
- general_requirement (integer)    # graduation requirement for general credits
- free_requirement (integer)       # graduation requirement for free credits
- missing_subjects (array of objects; each object has keys "type" and "description")
- completed_courses (array of strings) representing course codes that have been completed

Do not include any explanation or additional text.

PDF TEXT:
{pdf_text}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # 또는 사용 가능한 다른 모델(gpt-4, gpt-3.5-turbo 등)
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )
    raw_content = response.choices[0].message["content"].strip()
    print("debug: raw response content =", raw_content)
    
    # 만약 응답에 코드 블록 표시가 있으면 제거
    if raw_content.startswith("```"):
        lines = raw_content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    else:
        content = raw_content

    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        print("JSONDecodeError:", e)
        result = {}
    return result
