"""
챗봇 및 자연어 처리 관련 뷰들
Rasa 챗봇 연동 및 자연어 명령 파싱을 담당합니다.
"""

import json
import re
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ..utils import extract_number, get_korean_day_abbr, parse_time_range


# Rasa 서버 URL 설정
RASA_MODEL_ENDPOINT = "http://localhost:5005/model/parse"  # Rasa NLU 서버 URL
RASA_WEBHOOK_ENDPOINT = "http://localhost:5005/webhooks/rest/webhook"  # Rasa 대화 서버 URL


@csrf_exempt
def parse_constraints(request):
    """
    자연어 텍스트를 파싱하여 시간표 제약조건을 추출하는 뷰
    Rasa 서버와 통신하여 자연어 처리를 수행합니다.
    """
    data = json.loads(request.body)
    user_text = data.get("text", "")
    session_id = data.get("session_id", "default_user")

    print(request.body)

    # 1) 직접 Rasa 서버의 웹훅에 요청보내기
    try:
        rasa_response = requests.post(
            RASA_WEBHOOK_ENDPOINT,
            json={
                "sender": session_id,
                "message": user_text
            }
        )
        
        if rasa_response.status_code != 200:
            print('111')
            return JsonResponse({"error": f"Rasa 서버 응답 오류: {rasa_response.status_code}"}, status=500)
        
        # Rasa 응답 반환 (웹훅 형식)
        return JsonResponse(rasa_response.json(), safe=False)
        
    except Exception as e:
        print(str(e))
        return JsonResponse({"error": f"Rasa 서버 연결 오류: {str(e)}"}, status=500)


def extract_constraints_from_rasa_response(rasa_response):
    """
    Rasa NLU 응답에서 시간표 제약조건을 추출합니다.
    
    Args:
        rasa_response: Rasa 서버의 NLU 응답
        
    Returns:
        dict: 추출된 제약조건들
    """
    constraints = {
        "major_credits": None,
        "elective_credits": None,
        "required_courses": [],
        "free_days": [],
        "avoid_times": [],
        "avoid_time_ranges": [],
        "only_time_ranges": [],
        "exclude_courses": []
    }
    
    # 1. 엔티티 처리
    entities = rasa_response.get("entities", [])
    for entity in entities:
        entity_type = entity["entity"]
        value = entity["value"]
        
        if entity_type == "major_credits_entity":
            constraints["major_credits"] = extract_number(value)
        
        elif entity_type == "elective_credits_entity":
            constraints["elective_credits"] = extract_number(value)
        
        elif entity_type == "course_name_entity":
            # 2. 인텐트에 따라 처리 방식 결정
            intent = rasa_response.get("intent", {}).get("name", "")
            if intent == "modify_timetable":
                # 수정 요청일 경우: 과목 제외 목록에 추가
                if value not in constraints["exclude_courses"]:
                    constraints["exclude_courses"].append(value)
            else:
                # 일반 요청: 필수 과목 목록에 추가
                if value not in constraints["required_courses"]:
                    constraints["required_courses"].append(value)
        
        elif entity_type == "free_day_entity":
            day = get_korean_day_abbr(value)
            if day and day not in constraints["free_days"]:
                constraints["free_days"].append(day)
        
        elif entity_type == "free_day_keyword_entity":
            day = get_korean_day_abbr(value)
            if day and day not in constraints["free_days"]:
                constraints["free_days"].append(day)
        
        elif entity_type == "time_entity":
            # 시간 회피 처리 (예: "월요일 9시 피해줘")
            # 필요한 추가 컨텍스트 분석이 있다면 여기에 구현
            hour = extract_number(value)
            
            # 직전 엔티티가 요일인지 확인하는 로직이 필요할 수 있음
            # 간소화된 구현: 마지막으로 언급된 요일에 적용
            if hour is not None and constraints["free_days"]:
                last_day = constraints["free_days"][-1]
                constraints["avoid_times"].append({"day": last_day, "hour": hour})
        
        elif entity_type == "time_range_entity":
            # 시간대 회피 처리 (예: "오후 수업 피해줘")
            time_range = parse_time_range(value)
            if time_range:
                # 모든 요일 또는 특정 요일에 적용
                days = constraints["free_days"] if constraints["free_days"] else ["월", "화", "수", "목", "금"]
                time_range["days"] = days
                constraints["avoid_time_ranges"].append(time_range)

    return constraints 