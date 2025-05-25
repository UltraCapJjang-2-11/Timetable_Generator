# actions.py
import requests
import json
import re
from typing import Any, Text, Dict, List, Optional
import logging

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, UserUtteranceReverted, FollowupAction

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Django 서버 주소 (Rasa 서버와 Django 서버가 통신 가능해야 함)
DJANGO_PARSE_CONSTRAINTS_URL = "http://localhost:8000/parse_constraints/" # settings.py에 정의된 API 주소
DJANGO_GENERATE_TIMETABLE_URL = "http://localhost:8000/generate_timetable_stream/" # 시간표 생성 스트리밍 API

def get_korean_day_abbr(day_text: Text) -> Text:
    """한글 요일 전체 이름 또는 키워드를 약자로 변환"""
    day_text_processed = str(day_text).strip().lower()
    mapping = {
        "월요일": "월", "화요일": "화", "수요일": "수", "목요일": "목", "금요일": "금",
        "월": "월", "화": "화", "수": "수", "목": "목", "금": "금",
        "월공강": "월", "화공강": "화", "수공강": "수", "목공강": "목", "금공강": "금",
    }
    for key, value in mapping.items():
        if key in day_text_processed:
            return value
    return ""

def extract_number(text: str) -> Optional[int]:
    """문자열에서 숫자를 추출합니다."""
    if not text:
        return None
    
    # 숫자만 추출
    numbers = re.findall(r'\d+', text)
    if numbers:
        return int(numbers[0])
    return None

def parse_time_range(time_text: str) -> Dict[str, Any]:
    """시간대 텍스트를 분석하여 시간 범위 딕셔너리로 변환합니다."""
    if "오전" in time_text:
        return {"start_hour": 9, "end_hour": 12}
    elif "오후" in time_text:
        return {"start_hour": 13, "end_hour": 18}
    return {}

class ActionHandleTimetableRequest(Action):
    def name(self) -> Text:
        return "action_handle_timetable_request"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # 사용자 최근 메시지 (자연어 전체)
        latest_user_message = tracker.latest_message.get('text')
        latest_intent = tracker.latest_message.get('intent', {}).get('name', '')
        intent_confidence = tracker.latest_message.get('intent', {}).get('confidence', 0)

        logger.info(f"사용자 메시지: '{latest_user_message}', 인텐트: {latest_intent}, 확신도: {intent_confidence}")

        if not latest_user_message:
            dispatcher.utter_message(text="시간표 생성을 위한 사용자님의 최근 메시지를 찾을 수 없어요. 다시 말씀해주시겠어요?")
            return []

        # Rasa 모델로 분석된 정보 추출
        extracted_info, events = self.extract_constraints_from_rasa(tracker)
        
        logger.info(f"추출된 정보: {extracted_info}")

        # 정보가 부족한지 확인
        missing_slots = self.check_missing_required_slots(extracted_info)
        logger.debug(f"부족한 슬롯: {missing_slots}")
        
        # 전공 학점과 교양 학점 모두 있는 경우
        if "major_credits" not in missing_slots and "elective_credits" not in missing_slots:
            logger.info("전공 학점과 교양 학점 모두 확보됨, 시간표 생성 진행")
            
            # 확인 메시지 생성
            confirmation_message_parts = []
            if extracted_info.get("major_credits") is not None:
                confirmation_message_parts.append(f"전공 {extracted_info['major_credits']}학점")
            if extracted_info.get("elective_credits") is not None:
                confirmation_message_parts.append(f"교양 {extracted_info['elective_credits']}학점")
            if extracted_info.get("required_courses"):
                confirmation_message_parts.append(f"필수과목: {', '.join(extracted_info['required_courses'])}")
            if extracted_info.get("free_days"):
                days_str = ', '.join([f"{day}요일" for day in extracted_info['free_days']])
                confirmation_message_parts.append(f"공강요일: {days_str}")
            
            logger.info(f"최종 확인된 정보: {extracted_info}")
            
            # 확인 메시지 출력
            if confirmation_message_parts:
                confirmation_text = ", ".join(confirmation_message_parts) + " 조건으로 시간표를 생성합니다."
                
                # 프론트엔드로 데이터 전달
                custom_payload_for_frontend = {
                    "event_type": "initiate_timetable_generation_sse",
                    "major_credits": extracted_info.get("major_credits"),
                    "elective_credits": extracted_info.get("elective_credits"),
                    "required_courses": extracted_info.get("required_courses", []),
                    "free_days": extracted_info.get("free_days", []),
                    "avoid_times": extracted_info.get("avoid_times", []),
                    "avoid_time_ranges": extracted_info.get("avoid_time_ranges", []),
                    "only_time_ranges": extracted_info.get("only_time_ranges", []),
                    "exclude_courses": extracted_info.get("exclude_courses", []),
                    "existing_courses": []
                }
                
                # 디버깅 로그
                logger.info(f"시간표 생성 페이로드: {custom_payload_for_frontend}")
                
                # 시간표 생성 메시지 전송
                dispatcher.utter_message(text=confirmation_text)
                dispatcher.utter_message(text="웹 화면에서 시간표 생성 결과를 확인해주세요! ✨")
                dispatcher.utter_message(json_message=custom_payload_for_frontend)
                
                # 시간표 저장 버튼 추가
                dispatcher.utter_message(
                    text="시간표가 마음에 드시나요? 저장하시거나 수정할 수 있어요!",
                    buttons=[
                        {"title": "시간표 저장", "payload": "/save_timetable"},
                        {"title": "다시 생성", "payload": "시간표 다시 만들어줘"}
                    ]
                )
                
                # 대화 완료 후 슬롯 초기화
                logger.info("슬롯 초기화 시작")
                reset_events = [
                    SlotSet("major_credits_slot", None),
                    SlotSet("elective_credits_slot", None),
                    SlotSet("required_courses_slot", None),
                    SlotSet("free_days_slot", None),
                    SlotSet("time_slot", None),
                    SlotSet("time_range_slot", None),
                    SlotSet("requested_department_slot", None)
                ]
                
                # 중복 슬롯 설정 방지
                logger.info(f"필터링 전 이벤트 수: {len(events)}")
                filtered_events = []
                for e in events:
                    should_include = True
                    for r in reset_events:
                        if hasattr(e, 'key') and hasattr(r, 'key') and e.key == r.key:
                            logger.info(f"중복 슬롯 필터링: {e.key}")
                            should_include = False
                            break
                    if should_include:
                        filtered_events.append(e)
                
                logger.info(f"필터링 후 이벤트 수: {len(filtered_events)}")
                
                # 이벤트 반환
                logger.info("슬롯 초기화 완료, 이벤트 반환")
                return filtered_events + reset_events
            else:
                dispatcher.utter_message(text="시간표 생성을 위한 충분한 정보를 파악하지 못했어요. 다시 말씀해주세요.")
                return events
                
        # 전공 학점이 있고 교양 학점이 없는 경우 -> 교양 학점 질문
        elif "major_credits" not in missing_slots and "elective_credits" in missing_slots:
            logger.info("전공 학점은 있지만 교양 학점이 없음 -> 교양 학점 질문")
            dispatcher.utter_message(text="교양은 몇 학점 정도 들으실 계획인가요?")
            return events
            
        # 전공 학점이 없는 경우 -> 전공 학점 질문
        elif "major_credits" in missing_slots:
            logger.info("전공 학점 정보 없음 -> 전공 학점 질문")
            dispatcher.utter_message(text="전공은 몇 학점 정도 들으실 계획인가요?")
            return events
            
        # 교양 학점만 입력한 경우, 전공 학점이 있는지 확인
        elif latest_intent == "inform_elective_credits" and "major_credits" in missing_slots:
            logger.info("교양 학점만 제공됨, 전공 학점 질문")
            dispatcher.utter_message(text="전공은 몇 학점 정도 들으실 계획인가요?")
            return events
        
        # 기본 리턴
        return events

    def check_missing_required_slots(self, parsed_data: Dict[str, Any]) -> List[str]:
        """필수 정보 중 빠진 것이 있는지 확인합니다."""
        missing = []
        if parsed_data.get("major_credits") is None:
            missing.append("major_credits")
        if parsed_data.get("elective_credits") is None:
            missing.append("elective_credits")
        return missing

    def extract_constraints_from_rasa(self, tracker: Tracker) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Rasa 모델을 통해 추출된 엔티티 및 슬롯에서 시간표 제약조건을 추출합니다."""
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
        
        # 슬롯 설정을 위한 이벤트 목록
        events = []

        # 사용자 메시지 및 인텐트
        latest_message = tracker.latest_message.get('text', '')
        latest_intent = tracker.latest_message.get('intent', {}).get('name', '')
        
        logger.debug(f"메시지 분석 시작: '{latest_message}', 인텐트: {latest_intent}")
        
        # 먼저 단순 숫자 입력인지 확인 및 컨텍스트 파악
        is_simple_number = latest_message.strip().isdigit() or re.match(r'^\d+학점$', latest_message.strip())
        number_processed = False
        context_type = None  # 'major' 또는 'elective'
        
        if is_simple_number:
            num_value = extract_number(latest_message)
            logger.debug(f"단순 숫자 입력 감지: {num_value}")
            
            # 이전 봇 메시지 확인하여 전공/교양 구분
            for event in reversed(list(tracker.events)):
                if event.get('event') == 'bot' and event.get('text'):
                    last_bot_text = event.get('text', '')
                    logger.debug(f"최근 봇 메시지: '{last_bot_text}'")
                    
                    if "교양" in last_bot_text and "학점" in last_bot_text:
                        logger.info(f"교양 학점 질문 후 숫자 응답: {num_value}로 교양 학점 설정")
                        constraints["elective_credits"] = num_value
                        events.append(SlotSet("elective_credits_slot", str(num_value)))
                        number_processed = True
                        context_type = "elective"
                        break
                    elif "전공" in last_bot_text and "학점" in last_bot_text:
                        logger.info(f"전공 학점 질문 후 숫자 응답: {num_value}로 전공 학점 설정")
                        constraints["major_credits"] = num_value
                        events.append(SlotSet("major_credits_slot", str(num_value)))
                        number_processed = True
                        context_type = "major"
                        break
        
        # 슬롯에서 기존 정보 가져오기 (단순 숫자 컨텍스트 고려)
        major_credits_text = tracker.get_slot("major_credits_slot")
        elective_credits_text = tracker.get_slot("elective_credits_slot")
        required_courses = tracker.get_slot("required_courses_slot") or []
        free_days = tracker.get_slot("free_days_slot") or []
        
        # 슬롯 정보 로깅
        logger.debug(f"슬롯 상태 - 전공: {major_credits_text}, 교양: {elective_credits_text}")
        
        # 슬롯 정보를 제약조건으로 변환 (스마트 필터링)
        # 전공 슬롯 처리
        if major_credits_text:
            major_value = extract_number(major_credits_text)
            if major_value and constraints["major_credits"] is None:
                # 교양 학점 컨텍스트에서 전공 슬롯이 현재 입력값과 같으면 무시 (Rasa가 잘못 설정한 경우)
                if number_processed and context_type == "elective" and major_value == extract_number(latest_message):
                    logger.info(f"교양 학점 컨텍스트에서 전공 슬롯 값({major_value})이 현재 입력과 같아 무시")
                else:
                    constraints["major_credits"] = major_value
                    logger.debug(f"슬롯에서 전공 학점: {major_value}")
        
        # 교양 슬롯 처리  
        if elective_credits_text:
            elective_value = extract_number(elective_credits_text)
            if elective_value and constraints["elective_credits"] is None:
                # 전공 학점 컨텍스트에서 교양 슬롯이 현재 입력값과 같으면 무시 (Rasa가 잘못 설정한 경우)
                if number_processed and context_type == "major" and elective_value == extract_number(latest_message):
                    logger.info(f"전공 학점 컨텍스트에서 교양 슬롯 값({elective_value})이 현재 입력과 같아 무시")
                else:
                    constraints["elective_credits"] = elective_value
                    logger.debug(f"슬롯에서 교양 학점: {elective_value}")
        
        # 필수 과목 및 공강 정보 처리
        if required_courses:
            if isinstance(required_courses, list):
                constraints["required_courses"] = required_courses
            else:
                constraints["required_courses"] = [required_courses]
            
        if free_days:
            if isinstance(free_days, list):
                constraints["free_days"] = [get_korean_day_abbr(day) for day in free_days]
            else:
                constraints["free_days"] = [get_korean_day_abbr(free_days)]
        
        # 엔티티에서 정보 추출 (단순 숫자가 처리되지 않은 경우에만)
        if not number_processed:
            entities = tracker.latest_message.get('entities', [])
            logger.debug(f"엔티티 목록: {entities}")
            
            for entity in entities:
                entity_type = entity["entity"]
                value = entity["value"]
                logger.debug(f"엔티티 처리: {entity_type} = {value}")
                
                # 엔티티 타입별 처리
                if entity_type == "major_credits_entity" and constraints["major_credits"] is None:
                    major_value = extract_number(value)
                    if major_value:
                        constraints["major_credits"] = major_value
                        events.append(SlotSet("major_credits_slot", str(major_value)))
                        logger.debug(f"엔티티에서 전공 학점: {major_value}")
                
                elif entity_type == "elective_credits_entity" and constraints["elective_credits"] is None:
                    elective_value = extract_number(value)
                    if elective_value:
                        constraints["elective_credits"] = elective_value
                        events.append(SlotSet("elective_credits_slot", str(elective_value)))
                        logger.debug(f"엔티티에서 교양 학점: {elective_value}")
                
                elif entity_type == "course_name_entity":
                    course_name = value.strip()
                    if course_name and course_name not in constraints["required_courses"]:
                        constraints["required_courses"].append(course_name)
                        events.append(SlotSet("required_courses_slot", constraints["required_courses"]))
                        logger.debug(f"엔티티에서 필수 과목: {course_name}")
                
                elif entity_type == "free_day_entity":
                    day = get_korean_day_abbr(value)
                    logger.info(f"[DEBUG] free_day_entity 처리: 원본값='{value}', 변환값='{day}'")
                    if day and day not in constraints["free_days"]:
                        constraints["free_days"].append(day)
                        events.append(SlotSet("free_days_slot", constraints["free_days"]))
                        logger.info(f"엔티티에서 공강일 추가: {day}, 현재 공강일 목록: {constraints['free_days']}")
                
                elif entity_type == "free_day_keyword_entity":
                    # 금공강, 화공강 등의 키워드 처리
                    day = get_korean_day_abbr(value)
                    logger.info(f"[DEBUG] free_day_keyword_entity 처리: 원본값='{value}', 변환값='{day}'")
                    if day and day not in constraints["free_days"]:
                        constraints["free_days"].append(day)
                        events.append(SlotSet("free_days_slot", constraints["free_days"]))
                        logger.info(f"엔티티에서 공강 키워드 추가: {day}, 현재 공강일 목록: {constraints['free_days']}")
            
            # 인텐트별 추가 처리 (간단한 fallback - 엔티티로 처리되지 않은 경우에만)
            if latest_intent == "inform_elective_credits" and constraints["elective_credits"] is None:
                numbers = re.findall(r'\d+', latest_message)
                if numbers:
                    elective_value = int(numbers[0])
                    logger.debug(f"교양 학점 인텐트에서 직접 추출: {elective_value}")
                    constraints["elective_credits"] = elective_value
                    events.append(SlotSet("elective_credits_slot", str(elective_value)))

            if latest_intent == "inform_major_credits" and constraints["major_credits"] is None:
                numbers = re.findall(r'\d+', latest_message)
                if numbers:
                    major_value = int(numbers[0])
                    logger.debug(f"전공 학점 인텐트에서 직접 추출: {major_value}")
                    constraints["major_credits"] = major_value
                    events.append(SlotSet("major_credits_slot", str(major_value)))
            
            # 공강 관련 인텐트 처리 (fallback)
            if latest_intent == "inform_free_day" and not constraints["free_days"]:
                logger.info(f"[DEBUG] inform_free_day 인텐트 감지, 메시지: '{latest_message}'")
                # 요일 키워드 검색 (fallback)
                day_patterns = {
                    r'월요일|월': '월',
                    r'화요일|화': '화', 
                    r'수요일|수': '수',
                    r'목요일|목': '목',
                    r'금요일|금': '금'
                }
                for pattern, day_abbr in day_patterns.items():
                    if re.search(pattern, latest_message):
                        if day_abbr not in constraints["free_days"]:
                            constraints["free_days"].append(day_abbr)
                            events.append(SlotSet("free_days_slot", constraints["free_days"]))
                            logger.info(f"인텐트 fallback으로 공강일 추가: {day_abbr}")
            
            # request_timetable 인텐트에서 공강 관련 키워드 검색 (추가 fallback)
            if latest_intent == "request_timetable" and "공강" in latest_message and not constraints["free_days"]:
                logger.info(f"[DEBUG] request_timetable 인텐트에서 공강 키워드 감지, 메시지: '{latest_message}'")
                day_patterns = {
                    r'월요일|월': '월',
                    r'화요일|화': '화', 
                    r'수요일|수': '수',
                    r'목요일|목': '목',
                    r'금요일|금': '금'
                }
                for pattern, day_abbr in day_patterns.items():
                    if re.search(pattern, latest_message):
                        if day_abbr not in constraints["free_days"]:
                            constraints["free_days"].append(day_abbr)
                            events.append(SlotSet("free_days_slot", constraints["free_days"]))
                            logger.info(f"request_timetable fallback으로 공강일 추가: {day_abbr}")
            
            # modify_timetable 인텐트에서도 공강 관련 키워드 검색 (추가 fallback)
            if latest_intent == "modify_timetable" and "공강" in latest_message and not constraints["free_days"]:
                logger.info(f"[DEBUG] modify_timetable 인텐트에서 공강 키워드 감지, 메시지: '{latest_message}'")
                day_patterns = {
                    r'월요일|월': '월',
                    r'화요일|화': '화', 
                    r'수요일|수': '수',
                    r'목요일|목': '목',
                    r'금요일|금': '금'
                }
                for pattern, day_abbr in day_patterns.items():
                    if re.search(pattern, latest_message):
                        if day_abbr not in constraints["free_days"]:
                            constraints["free_days"].append(day_abbr)
                            events.append(SlotSet("free_days_slot", constraints["free_days"]))
                            logger.info(f"modify_timetable fallback으로 공강일 추가: {day_abbr}")
        else:
            logger.info("단순 숫자 입력이 처리되었으므로 엔티티/인텐트 기반 처리 건너뜀")
        
        logger.info(f"최종 추출 결과: {constraints}")
        return constraints, events

class ActionSaveTimetable(Action):
    def name(self) -> Text:
        return "action_save_timetable"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        logger.info("시간표 저장 액션 실행")
        
        # 프론트엔드로 시간표 저장 이벤트 전송
        save_payload = {
            "event_type": "save_timetable",
            "message": "시간표를 저장합니다."
        }
        
        dispatcher.utter_message(text="시간표를 저장했습니다! 저장된 시간표는 '내 시간표 관리' 페이지에서 확인할 수 있어요. 📚")
        dispatcher.utter_message(json_message=save_payload)
        
        return []


class ActionExcludeCourseAndRegenerate(Action):
    def name(self) -> Text:
        return "action_exclude_course_and_regenerate"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # 사용자 메시지에서 제외할 과목 추출
        latest_message = tracker.latest_message.get('text', '')
        entities = tracker.latest_message.get('entities', [])
        
        exclude_courses = []
        for entity in entities:
            if entity["entity"] == "course_name_entity":
                course_name = entity["value"].strip()
                if course_name:
                    exclude_courses.append(course_name)
        
        logger.info(f"제외할 과목: {exclude_courses}")
        
        if not exclude_courses:
            dispatcher.utter_message(text="제외할 과목을 찾을 수 없어요. 어떤 과목을 빼고 싶으신가요?")
            return []
        
        # 기존 제약조건 가져오기 (슬롯에서)
        major_credits_text = tracker.get_slot("major_credits_slot")
        elective_credits_text = tracker.get_slot("elective_credits_slot")
        free_days = tracker.get_slot("free_days_slot") or []
        
        # 학점 추출
        major_credits = None
        elective_credits = None
        
        if major_credits_text:
            major_value = extract_number(major_credits_text)
            if major_value:
                major_credits = major_value
                
        if elective_credits_text:
            elective_value = extract_number(elective_credits_text)
            if elective_value:
                elective_credits = elective_value
        
        # 공강일 처리
        processed_free_days = []
        if free_days:
            if isinstance(free_days, list):
                processed_free_days = [get_korean_day_abbr(day) for day in free_days]
            else:
                processed_free_days = [get_korean_day_abbr(free_days)]
        
        # 제외 과목 메시지
        exclude_msg = ", ".join(exclude_courses)
        dispatcher.utter_message(text=f"{exclude_msg}을(를) 제외하고 시간표를 다시 생성합니다.")
        
        # 프론트엔드로 재생성 이벤트 전송
        regenerate_payload = {
            "event_type": "exclude_and_regenerate_timetable",
            "major_credits": major_credits,
            "elective_credits": elective_credits,
            "free_days": processed_free_days,
            "exclude_courses": exclude_courses,
            "keep_existing_courses": True  # 나머지 과목은 유지
        }
        
        logger.info(f"재생성 페이로드: {regenerate_payload}")
        
        dispatcher.utter_message(text="웹 화면에서 새로운 시간표를 확인해주세요! ✨")
        dispatcher.utter_message(json_message=regenerate_payload)
        
        return []