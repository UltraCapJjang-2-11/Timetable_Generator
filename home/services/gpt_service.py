import openai
import json
from django.conf import settings

# 실제 API 키는 settings 또는 환경변수를 통해 관리하세요.
openai.api_key = settings.OPENAI_API_KEY

def extract_graduation_info_from_text(pdf_text: str) -> dict:
    """
    PDF 텍스트에서 졸업 이수 정보를 추출합니다.
    
    PDF 텍스트는 두 개의 주요 행을 포함합니다.
      1. 첫 번째 행은 졸업 기준 학점 정보를 나타내며,
         특히 교양(일반 교육) 부문은 전체 기준(예, 최소:42, 최대:56)와 함께,
         교양 세부 항목별 required 학점(순서대로, 예: 18, 12, 9, 3, 0)이 제공됩니다.
      2. 두 번째 행은 학생이 실제 이수한 학점 정보를 나타냅니다.
      
    또한 학생 기본정보(학번, 이름, 전공, 학년)도 포함되어 있습니다.
    
    예상 출력 JSON 구조 예시는 다음과 같습니다:
    
    {
      "user_student_id": "2022078070",
      "user_name": "윤시훈",
      "user_major": "소프트웨어학부",
      "user_year": "4학년",
      "total_credits": 140,
      "major_credits": 44,
      "general_credits": 39,
      "free_credits": 14,
      "total_requirement": 140,
      "major_requirement": {"전공필수": 30, "전공선택": 54},
      "general_requirement": {"required": {"minimum": 42, "maximum": 56}},
      "free_requirement": 0,
      "missing_subjects": [ { "type": "...", "description": "..." }, ... ],
      "completed_courses": [ "과목코드1", "과목코드2", ... ],
      "missing_general_sub": {
          "개신기초교양": 3,
          "자연이공계기초": 0,
          "일반교양": 0,
          "확대교양": 0,
          "OCU기타": 0
      },
      "detailed_credits": {
         "교양": {
           "required": {
               "개신기초교양": integer,    // PDF에서 추출된 교양 세부 required 값
               "자연이공계기초": integer,
               "일반교양": integer,
               "확대교양": integer,
               "OCU기타": integer
           },
           "breakdown": {
             "개신기초교양": {"earned": integer},
             "자연이공계기초": {"earned": integer},
             "일반교양": {"earned": integer},
             "확대교양": {"earned": integer},
             "OCU기타": {"earned": integer}
           }
         },
         "전공": {
           "전공필수": {"required": 30, "earned": 23},
           "전공선택": {"required": 54, "earned": 21}
         },
         "일반선택": {"required": 0, "earned": 14},
         "졸업": {"total": 140, "earned": 97},
         "summary": {
             "교양이수합": 39,
             "전공이수합": 44,
             "overall": 97,
             "평점": 3.68,
             "백분율": 90.8,
             "등급": "A0"
         }
      }
    }
    
    출력은 반드시 valid JSON이어야 하며, 추가 설명 없이 JSON 객체만 내보내십시오.
    """
    system_prompt = (
        "You are a helpful assistant specialized in extracting graduation information from academic documents."
    )
    user_prompt = f"""
Below is the extracted text from a graduation requirements PDF.
The text contains two main rows:
  - The first row shows the graduation requirement credits for various categories.
    For the general education section, it provides an overall requirement (e.g., [최소:42/최대:56])
    and a breakdown into subcategories. The breakdown is provided as a sequence of numbers (e.g., 18, 12, 9, 3, 0)
    which correspond in order to the required credits for: 개신기초교양, 자연이공계기초, 일반교양, 확대교양, and OCU기타.
  - The second row shows the credits that the student has earned in the same categories.
In addition, extract the student's basic info.
Please output ONLY valid JSON according to the following structure without any extra text:

{{
  "user_student_id": string,
  "user_name": string,
  "user_major": string,
  "user_year": string,
  "total_credits": integer,
  "major_credits": integer,
  "general_credits": integer,
  "free_credits": integer,
  "total_requirement": integer,
  "major_requirement": {{"전공필수": integer, "전공선택": integer}},
  "general_requirement": {{"required": {{"minimum": integer, "maximum": integer}}}},
  "free_requirement": integer,
  "missing_subjects": [ {{ "type": string, "description": string }}, ... ],
  "completed_courses": [ string, ... ],
  "missing_general_sub": {{
      "개신기초교양": integer,
      "자연이공계기초": integer,
      "일반교양": integer,
      "확대교양": integer,
      "OCU기타": integer
  }},
  "detailed_credits": {{
      "교양": {{
         "required": {{
             "개신기초교양": integer,
             "자연이공계기초": integer,
             "일반교양": integer,
             "확대교양": integer,
             "OCU기타": integer
         }},
         "breakdown": {{
             "개신기초교양": {{"earned": integer}},
             "자연이공계기초": {{"earned": integer}},
             "일반교양": {{"earned": integer}},
             "확대교양": {{"earned": integer}},
             "OCU기타": {{"earned": integer}}
         }}
      }},
      "전공": {{
         "전공필수": {{"required": integer, "earned": integer}},
         "전공선택": {{"required": integer, "earned": integer}}
      }},
      "일반선택": {{"required": integer, "earned": integer}},
      "졸업": {{"total": integer, "earned": integer}},
      "summary": {{
         "교양이수합": integer,
         "전공이수합": integer,
         "overall": integer,
         "평점": number,
         "백분율": number,
         "등급": string
      }}
  }}
}}

Do not include any explanation or additional text.

PDF TEXT:
{pdf_text}
"""
    response = openai.ChatCompletion.create(
         model="gpt-4o-mini",
         messages=[
             {"role": "system", "content": system_prompt},
             {"role": "user", "content": user_prompt},
         ],
         temperature=0.0,
    )
    raw_content = response.choices[0].message["content"].strip()
    print("debug: raw response content =", raw_content)
    
    # Remove code block wrapper if present.
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
