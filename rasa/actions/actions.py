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

        # 슬롯에서 정보 가져오기
        major_credits_text = tracker.get_slot("major_credits_slot")
        elective_credits_text = tracker.get_slot("elective_credits_slot")
        required_courses_list = tracker.get_slot("required_courses_slot")
        free_days_text_list = tracker.get_slot("free_days_slot")

        # 사용자 최근 메시지 (자연어 전체)
        latest_user_message = tracker.latest_message.get('text')
        latest_intent = tracker.latest_message.get('intent', {}).get('name', '')
        intent_confidence = tracker.latest_message.get('intent', {}).get('confidence', 0)

        logger.info(f"사용자 메시지: '{latest_user_message}', 인텐트: {latest_intent}, 확신도: {intent_confidence}")
        logger.info(f"현재 슬롯 상태 - 전공: {major_credits_text}, 교양: {elective_credits_text}")

        if not latest_user_message:
            dispatcher.utter_message(text="시간표 생성을 위한 사용자님의 최근 메시지를 찾을 수 없어요. 다시 말씀해주시겠어요?")
            return []

        # Rasa 모델로 분석된 정보 추출, 슬롯 설정을 위한 이벤트 반환
        extracted_info, events = self.extract_constraints_from_rasa(tracker)
        
        # 특별 처리: 단순 숫자만 입력된 경우
        # 이전 질문에 따라 전공 또는 교양으로 분류
        if latest_user_message.strip().isdigit() or re.match(r'^\d+학점$', latest_user_message.strip()):
            num_value = extract_number(latest_user_message)
            logger.info(f"숫자만 입력됨: {num_value}")
            
            # 마지막으로 봇이 물어본 질문이 교양 학점인 경우
            last_bot_message = None
            for event in reversed(list(tracker.events)):
                if event.get('event') == 'bot' and event.get('text'):
                    last_bot_text = event.get('text', '')
                    logger.debug(f"마지막 봇 메시지: '{last_bot_text}'")
                    
                    if "교양" in last_bot_text and "학점" in last_bot_text:
                        logger.info(f"교양 학점 질문에 대한 숫자 응답으로 판단: {num_value}")
                        extracted_info["elective_credits"] = num_value
                        events.append(SlotSet("elective_credits_slot", str(num_value)))
                        
                    elif "전공" in last_bot_text and "학점" in last_bot_text:
                        logger.info(f"전공 학점 질문에 대한 숫자 응답으로 판단: {num_value}")
                        extracted_info["major_credits"] = num_value
                        events.append(SlotSet("major_credits_slot", str(num_value)))
                    break
        
        # 교양 키워드 + 숫자 조합 감지
        if "교양" in latest_user_message and not extracted_info.get("elective_credits"):
            logger.debug(f"교양 키워드 발견 - 직접 숫자 추출: '{latest_user_message}'")
            numbers = re.findall(r'\d+', latest_user_message)
            if numbers:
                num_value = int(numbers[0])
                logger.info(f"교양 키워드와 함께 숫자 발견: {num_value}")
                extracted_info["elective_credits"] = num_value
                events.append(SlotSet("elective_credits_slot", str(num_value)))
        
        # 정보가 부족한지 확인
        missing_slots = self.check_missing_required_slots(extracted_info)
        logger.debug(f"부족한 슬롯: {missing_slots}")
        
        # 교양 학점이 이미 제공되었는지 확인하는 플래그 - 무한 루프 방지
        elective_credits_provided = extracted_info.get("elective_credits") is not None
        major_credits_provided = extracted_info.get("major_credits") is not None
        
        # 첫 번째 메시지에서 공강 요일과 학점 정보가 모두 있는지 체크 (예: "화요일 공강으로 전공 9학점 교양 9학점")
        if ("공강" in latest_user_message or "화요일" in latest_user_message or "월요일" in latest_user_message or 
            "수요일" in latest_user_message or "목요일" in latest_user_message or "금요일" in latest_user_message):
            logger.info("공강 관련 키워드 발견, 메시지에서 학점 정보도 확인")
            
            # 전공 학점이 없는 경우 추출 시도
            if not major_credits_provided and "전공" in latest_user_message:
                major_match = re.search(r'전공\s*(\d+)\s*학점', latest_user_message)
                if major_match:
                    major_value = int(major_match.group(1))
                    logger.info(f"첫 메시지에서 전공 학점 추출: {major_value}")
                    extracted_info["major_credits"] = major_value
                    events.append(SlotSet("major_credits_slot", str(major_value)))
                    major_credits_provided = True
            
            # 교양 학점이 없는 경우 추출 시도
            if not elective_credits_provided and "교양" in latest_user_message:
                # 전체 문장에서 "교양 X학점" 패턴 검색
                elective_match = re.search(r'교양\s*(\d+)\s*학점', latest_user_message)
                if elective_match:
                    elective_value = int(elective_match.group(1))
                    logger.info(f"첫 메시지에서 교양 학점 추출: {elective_value}")
                    extracted_info["elective_credits"] = elective_value
                    events.append(SlotSet("elective_credits_slot", str(elective_value)))
                    elective_credits_provided = True
                else:
                    # 문장에 "교양" 키워드 주변 분석 - 더 넓은 범위 확인
                    edu_idx = latest_user_message.find("교양")
                    edu_part = latest_user_message[max(0, edu_idx-15):min(len(latest_user_message), edu_idx+20)]
                    logger.debug(f"교양 키워드 확장 범위: '{edu_part}'")
                    
                    # 교양 키워드 뒤에 있는 숫자 우선 확인 (더 정확)
                    after_keyword = edu_part[edu_part.find("교양"):]
                    after_numbers = re.findall(r'\d+', after_keyword)
                    
                    if after_numbers:
                        # 교양 키워드 뒤에 있는 첫 번째 숫자 사용 (높은 정확도)
                        elective_value = int(after_numbers[0])
                        logger.info(f"첫 메시지 교양 키워드 후 숫자 추출: {elective_value}")
                        if elective_value <= 30:  # 합리적인 학점 범위 확인
                            extracted_info["elective_credits"] = elective_value
                            events.append(SlotSet("elective_credits_slot", str(elective_value)))
                            elective_credits_provided = True
                    else:
                        # 전체 문자열에서 숫자 추출
                        edu_numbers = re.findall(r'\d+', edu_part)
                        
                        # "전공9학점 교양6학점"와 같은 패턴 처리
                        if "전공" in edu_part and len(edu_numbers) >= 2:
                            # 전공 키워드 위치 확인
                            major_idx = edu_part.find("전공")
                            
                            # 전공과 교양 사이 순서 확인
                            if major_idx < edu_idx:  # 전공이 교양보다 앞에 있음
                                if len(edu_numbers) >= 2:  # 최소 두 개의 숫자가 있어야 함
                                    # 교양에 가까운 숫자 선택
                                    # 전공 키워드 뒤 숫자는 전공 학점, 교양 키워드 뒤 숫자는 교양 학점
                                    major_after = edu_part[major_idx:edu_idx]
                                    major_numbers = re.findall(r'\d+', major_after)
                                    
                                    if major_numbers and len(edu_numbers) > len(major_numbers):
                                        # 전공 숫자를 제외한 나머지 중 교양에 가장 가까운 숫자
                                        for num in edu_numbers:
                                            if num not in major_numbers:
                                                elective_value = int(num)
                                                if elective_value <= 30:
                                                    logger.info(f"전공-교양 패턴에서 교양 학점 추출: {elective_value}")
                                                    extracted_info["elective_credits"] = elective_value
                                                    events.append(SlotSet("elective_credits_slot", str(elective_value)))
                                                    elective_credits_provided = True
                                                    break
            
            # 슬롯 상태 갱신
            missing_slots = self.check_missing_required_slots(extracted_info)
            logger.debug(f"공강 키워드 처리 후 부족한 슬롯: {missing_slots}")
        
        # 더 나은 인텐트 감지 - 인텐트 감지가 낮은 경우 메시지 내용으로 추정
        if intent_confidence < 0.7 and latest_user_message:
            logger.info(f"인텐트 확신도가 낮음({intent_confidence}), 메시지 내용으로 추정")
            
            # 교양 관련 키워드인지 확인
            if "교양" in latest_user_message:
                logger.debug("메시지에서 교양 키워드 발견")
                
                # 정확한 '교양 X학점' 패턴 먼저 시도
                elective_match = re.search(r'교양\s*(\d+)\s*학점', latest_user_message)
                if elective_match:
                    elective_value = int(elective_match.group(1))
                    logger.info(f"인텐트 확신도 낮음: 교양 패턴에서 정확히 매칭된 학점: {elective_value}")
                    extracted_info["elective_credits"] = elective_value
                    events.append(SlotSet("elective_credits_slot", str(elective_value)))
                    elective_credits_provided = True
                else:
                    # 교양 키워드 주변 분석
                    edu_idx = latest_user_message.find("교양")
                    edu_part = latest_user_message[max(0, edu_idx-15):min(len(latest_user_message), edu_idx+20)]
                    
                    # 교양 키워드 뒤에 있는 숫자 우선 확인
                    after_keyword = latest_user_message[edu_idx:]
                    after_numbers = re.findall(r'\d+', after_keyword)
                    
                    if after_numbers:
                        # 교양 키워드 바로 뒤 숫자를 우선 사용
                        elective_value = int(after_numbers[0])
                        logger.info(f"인텐트 확신도 낮음: 교양 키워드 뒤 숫자 추출: {elective_value}")
                        extracted_info["elective_credits"] = elective_value
                        events.append(SlotSet("elective_credits_slot", str(elective_value)))
                        elective_credits_provided = True
                    else:
                        # 전체 메시지에서 숫자 분석
                        all_nums = re.findall(r'\d+', latest_user_message)
                        if all_nums and len(all_nums) >= 2:
                            # 전공 키워드 분석
                            if "전공" in latest_user_message:
                                major_idx = latest_user_message.find("전공")
                                # 전공이 교양보다 앞에 있는 경우
                                if major_idx < edu_idx:
                                    # 전공 키워드 주변 숫자
                                    major_part = latest_user_message[major_idx:edu_idx]
                                    major_nums = re.findall(r'\d+', major_part)
                                    
                                    if major_nums and len(all_nums) > len(major_nums):
                                        # 교양 쪽에 있는 숫자를 교양 학점으로 설정
                                        remaining_nums = [n for n in all_nums if n not in major_nums]
                                        if remaining_nums:
                                            elective_value = int(remaining_nums[0])
                                            logger.info(f"인텐트 확신도 낮음: 전공-교양 구분 추출 학점: {elective_value}")
                                            extracted_info["elective_credits"] = elective_value
                                            events.append(SlotSet("elective_credits_slot", str(elective_value)))
                                            elective_credits_provided = True
                                else:
                                    # 교양이 전공보다 앞에 있는 경우
                                    edu_part = latest_user_message[edu_idx:major_idx]
                                    edu_nums = re.findall(r'\d+', edu_part)
                                    if edu_nums:
                                        elective_value = int(edu_nums[0])
                                        logger.info(f"인텐트 확신도 낮음: 교양-전공 순서 학점: {elective_value}")
                                        extracted_info["elective_credits"] = elective_value
                                        events.append(SlotSet("elective_credits_slot", str(elective_value)))
                                        elective_credits_provided = True
                            # 전공 키워드가 없는 경우, 메시지에 여러 숫자가 있다면 두번째 숫자를 교양으로 가정
                            elif len(all_nums) >= 2:
                                # 전공은 주로 앞에 언급되므로, 두 번째 숫자를 교양으로 가정
                                elective_value = int(all_nums[1])
                                logger.info(f"인텐트 확신도 낮음: 여러 숫자 중 두번째 선택: {elective_value}")
                                extracted_info["elective_credits"] = elective_value
                                events.append(SlotSet("elective_credits_slot", str(elective_value)))
                                elective_credits_provided = True
                            else:
                                # 단일 숫자만 있으면 안전하게 첫 번째 숫자 사용
                                elective_value = int(all_nums[0])
                                logger.info(f"인텐트 확신도 낮음: 단일 숫자 추출: {elective_value}")
                                extracted_info["elective_credits"] = elective_value
                                events.append(SlotSet("elective_credits_slot", str(elective_value)))
                                elective_credits_provided = True
                
                # 슬롯 상태 갱신
                missing_slots = self.check_missing_required_slots(extracted_info)
        
        # 교양 학점과 전공 학점 모두 있는 경우
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
                
                # 중복 슬롯 설정 방지를 위한 이벤트 필터링 (수정)
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
            return events  # 여기서 슬롯 설정 이벤트 반환
            
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
        
        # 기본 리턴 추가
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
        confidence = tracker.latest_message.get('intent', {}).get('confidence', 0)
        logger.debug(f"메시지 분석 시작: '{latest_message}', 인텐트: {latest_intent}, 확신도: {confidence}")
        
        # 1. 슬롯에서 정보 가져오기
        major_credits_text = tracker.get_slot("major_credits_slot")
        elective_credits_text = tracker.get_slot("elective_credits_slot")
        required_courses = tracker.get_slot("required_courses_slot") or []
        free_days = tracker.get_slot("free_days_slot") or []
        
        # 슬롯 정보 로깅
        logger.debug(f"슬롯 상태 - 전공: {major_credits_text}, 교양: {elective_credits_text}")
        
        # 2. 슬롯 정보를 제약조건으로 변환
        if major_credits_text:
            major_value = extract_number(major_credits_text)
            if major_value:
                constraints["major_credits"] = major_value
                logger.debug(f"슬롯에서 전공 학점: {major_value}")
        
        if elective_credits_text:
            elective_value = extract_number(elective_credits_text)
            if elective_value:
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
        
        # 3. 단일 숫자 처리 - 이전 질문 맥락에 따라 전공 또는 교양 학점으로 할당
        if latest_message.strip().isdigit() or re.match(r'^\d+학점$', latest_message.strip()):
            num_value = extract_number(latest_message)
            logger.debug(f"단일 숫자 입력: {num_value}")
            
            # 이전 봇 메시지 확인
            previous_messages = list(tracker.events)
            bot_messages = [
                e for e in previous_messages 
                if e.get('event') == 'bot' and e.get('text') and len(previous_messages) - previous_messages.index(e) <= 4
            ]
            
            if bot_messages:
                last_bot_message = bot_messages[-1].get('text', '')
                logger.debug(f"최근 봇 메시지: '{last_bot_message}'")
                
                if "교양" in last_bot_message and "학점" in last_bot_message:
                    logger.info(f"교양 학점 질문 후 숫자 응답: {num_value}로 교양 학점 설정")
                    constraints["elective_credits"] = num_value
                    events.append(SlotSet("elective_credits_slot", str(num_value)))
                elif "전공" in last_bot_message and "학점" in last_bot_message:
                    logger.info(f"전공 학점 질문 후 숫자 응답: {num_value}로 전공 학점 설정")
                    constraints["major_credits"] = num_value
                    events.append(SlotSet("major_credits_slot", str(num_value)))
        
        # 4. 전체 메시지 직접 분석 (인텐트와 관계없이)
        # 교양 학점 직접 추출 시도
        if "교양" in latest_message and constraints["elective_credits"] is None:
            # 교양 주변 텍스트 추출 (더 넓은 범위로 추출)
            edu_idx = latest_message.find("교양")
            edu_part = latest_message[max(0, edu_idx-15):min(len(latest_message), edu_idx+20)]
            logger.debug(f"교양 주변 텍스트 확장: '{edu_part}'")
            
            # 정확한 패턴 매칭 먼저 시도 ("교양 6학점" 형식)
            elective_match = re.search(r'교양\s*(\d+)\s*학점', edu_part)
            if elective_match:
                edu_value = int(elective_match.group(1))
                logger.info(f"교양 패턴에서 정확히 매칭된 학점: {edu_value}")
                constraints["elective_credits"] = edu_value
                events.append(SlotSet("elective_credits_slot", str(edu_value)))
            else:
                # 교양 키워드 뒤에 있는 숫자 추출 시도 - 이 부분이 중요
                after_keyword = edu_part[edu_part.find("교양"):]
                after_numbers = re.findall(r'\d+', after_keyword)
                
                if after_numbers:
                    # 교양 키워드 뒤에 있는 첫 번째 숫자 사용 (더 정확한 방법)
                    edu_value = int(after_numbers[0])
                    logger.info(f"교양 키워드 바로 뒤 숫자 추출: {edu_value}")
                    if edu_value <= 30:  # 합리적인 학점 범위
                        constraints["elective_credits"] = edu_value
                        events.append(SlotSet("elective_credits_slot", str(edu_value)))
                else:
                    # 일반적인 숫자 추출 시도 - 이 부분은 순서를 변경
                    edu_numbers = re.findall(r'\d+', edu_part)
                    if edu_numbers:
                        # 가장 가까운 숫자(교양 앞의 마지막 숫자나 전체 중 마지막 숫자) 선택
                        before_keyword = edu_part[:edu_part.find("교양")]
                        before_numbers = re.findall(r'\d+', before_keyword)
                        
                        if before_numbers and len(before_numbers) > 0:
                            # 교양 앞에 있는 마지막 숫자는 아마도 전공 학점일 가능성이 높음
                            # 따라서 앞의 숫자는 사용하지 않음
                            logger.debug(f"교양 앞에 숫자 발견: {before_numbers}, 이는 전공 학점일 가능성이 높음")
                            
                            # 앞의 숫자가 전공 학점으로 이미 인식된 경우, 교양 학점은 보통 같거나 조금 다름
                            if constraints["major_credits"] is not None:
                                # 간단한 휴리스틱: 전공과 비슷한 수준의 학점으로 가정
                                if len(edu_numbers) > 1:
                                    # 첫 번째와 마지막 숫자 중 전공과 다른 숫자를 선택
                                    major_val = constraints["major_credits"]
                                    first_val = int(edu_numbers[0])
                                    last_val = int(edu_numbers[-1])
                                    
                                    if first_val != major_val and first_val <= 30:
                                        edu_value = first_val
                                    elif last_val != major_val and last_val <= 30:
                                        edu_value = last_val
                                    else:
                                        # 모든 숫자가 전공과 같으면 그냥 사용
                                        edu_value = int(edu_numbers[-1])
                                    
                                    logger.info(f"교양 학점으로 전공과 구분하여 추출: {edu_value}")
                                    constraints["elective_credits"] = edu_value
                                    events.append(SlotSet("elective_credits_slot", str(edu_value)))
                        else:
                            # 교양 앞에 숫자가 없다면 마지막 숫자를 사용
                            edu_value = int(edu_numbers[-1])
                            if edu_value <= 30:  # 합리적인 학점 범위
                                logger.debug(f"교양 주변에서 마지막 숫자 추출: {edu_value}")
                                constraints["elective_credits"] = edu_value
                                events.append(SlotSet("elective_credits_slot", str(edu_value)))
        
        # 공강 요일 추출 시도 - 더 정확한 패턴 사용
        days_pattern = r'(월|화|수|목|금)요일.*공강|공강.*?(월|화|수|목|금)요일|(월|화|수|목|금)요일을?\s*공강으로'
        for match in re.finditer(days_pattern, latest_message):
            # 첫 번째 매칭 그룹이 있으면 사용, 없으면 두 번째 또는 세 번째 그룹 사용
            day = None
            for i in range(1, 4):
                if match.group(i):
                    day = match.group(i)
                    break
                    
            if day and day not in constraints["free_days"]:
                logger.info(f"공강 요일 발견: {day}요일")
                constraints["free_days"].append(get_korean_day_abbr(day))
                events.append(SlotSet("free_days_slot", constraints["free_days"]))
                
        # 첫 번째 메시지에서 공강 요일 있을 경우 반드시 확인
        if "공강" in latest_message or "요일" in latest_message:
            # 요일 패턴 검색
            days = ["월", "화", "수", "목", "금"]
            for day in days:
                day_pattern = f"{day}요일"
                if day_pattern in latest_message and day not in constraints["free_days"]:
                    logger.info(f"요일 패턴으로 공강 의도 추정: {day}요일")
                    constraints["free_days"].append(day)
                    events.append(SlotSet("free_days_slot", constraints["free_days"]))
        
        # 전공 학점 직접 추출 시도
        if "전공" in latest_message and constraints["major_credits"] is None:
            major_idx = latest_message.find("전공")
            major_part = latest_message[max(0, major_idx-10):min(len(latest_message), major_idx+15)]
            logger.debug(f"전공 주변 텍스트: '{major_part}'")
            
            # 정확한 패턴 매칭 먼저 시도 ("전공 9학점" 형식)
            major_match = re.search(r'전공\s*(\d+)\s*학점', major_part)
            if major_match:
                major_value = int(major_match.group(1))
                logger.info(f"전공 패턴에서 정확히 매칭된 학점: {major_value}")
                constraints["major_credits"] = major_value
                events.append(SlotSet("major_credits_slot", str(major_value)))
            else:
                # 일반적인 숫자 추출 시도
                major_numbers = re.findall(r'\d+', major_part)
                if major_numbers:
                    # 전공과 가장 가까운 숫자를 선택 (첫 번째 숫자)
                    major_value = int(major_numbers[0])
                    if major_value <= 30:  # 합리적인 학점 범위
                        logger.debug(f"전공 주변에서 숫자 추출: {major_value}")
                        constraints["major_credits"] = major_value
                        events.append(SlotSet("major_credits_slot", str(major_value)))
        
        # 5. 엔티티 처리
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
            
            # 필수 과목, 공강일 등 기타 엔티티 처리...
        
        # 6. 인텐트별 특수 처리
        # 교양 학점 관련 인텐트
        if latest_intent == "inform_elective_credits" and constraints["elective_credits"] is None:
            numbers = re.findall(r'\d+', latest_message)
            if numbers:
                elective_value = int(numbers[0])
                logger.debug(f"교양 학점 인텐트에서 직접 추출: {elective_value}")
                constraints["elective_credits"] = elective_value
                events.append(SlotSet("elective_credits_slot", str(elective_value)))
            else:
                # 교양 학점 인텐트인데 숫자가 없는 경우 기본값 설정 (선택적)
                logger.warning("교양 학점 인텐트지만 숫자 없음")
                
                # "." 입력과 같은 특수 경우 처리
                if latest_message.strip() in [".", "...", "예", "네", "ㅇㅇ", "yes", "y"]:
                    logger.info("간단한 응답을 전공/교양 확인으로 처리")
                    # 이전 교양 질문이 있었는지 확인
                    bot_history = [e for e in tracker.events if e.get('event') == 'bot' and e.get('text')][-3:]
                    for bot_event in reversed(bot_history):
                        bot_text = bot_event.get('text', '')
                        if "교양" in bot_text and "학점" in bot_text:
                            # 기본 교양 학점 설정 (예: 전공과 동일하게)
                            if constraints["major_credits"] is not None:
                                elective_value = constraints["major_credits"]
                                logger.info(f"'.' 입력 처리: 교양 학점을 전공과 동일하게 설정 {elective_value}")
                                constraints["elective_credits"] = elective_value
                                events.append(SlotSet("elective_credits_slot", str(elective_value)))
                            else:
                                # 기본값 설정
                                logger.info("'.' 입력 처리: 교양 학점 기본값 9 설정")
                                constraints["elective_credits"] = 9
                                events.append(SlotSet("elective_credits_slot", "9"))
                            break

        # 전공 학점 관련 인텐트
        if latest_intent == "inform_major_credits" and constraints["major_credits"] is None:
            numbers = re.findall(r'\d+', latest_message)
            if numbers:
                major_value = int(numbers[0])
                logger.debug(f"전공 학점 인텐트에서 직접 추출: {major_value}")
                constraints["major_credits"] = major_value
                events.append(SlotSet("major_credits_slot", str(major_value)))
        
        # 7. 마지막 점검 - 메시지에서 전체 문맥 고려
        if "들을래" in latest_message or "할래" in latest_message or "듣고 싶어" in latest_message:
            logger.debug("'들을래/할래/듣고 싶어' 표현 발견, 문맥 분석")
            
            # 교양 학점이 없지만 메시지에 숫자가 있는 경우
            if constraints["elective_credits"] is None and "교양" in latest_message:
                numbers = re.findall(r'\d+', latest_message)
                if numbers:
                    elective_value = int(numbers[0])
                    logger.info(f"'~하고 싶어' 문맥에서 교양 학점으로 {elective_value} 설정")
                    constraints["elective_credits"] = elective_value
                    events.append(SlotSet("elective_credits_slot", str(elective_value)))
            
            # 전공 학점이 없지만 메시지에 숫자가 있는 경우
            if constraints["major_credits"] is None and "전공" in latest_message:
                numbers = re.findall(r'\d+', latest_message)
                if numbers:
                    major_value = int(numbers[0])
                    logger.info(f"'~하고 싶어' 문맥에서 전공 학점으로 {major_value} 설정")
                    constraints["major_credits"] = major_value
                    events.append(SlotSet("major_credits_slot", str(major_value)))
        
        # 8. 마지막 안전 장치: 단일 숫자 입력(인텐트 감지 실패 시)
        if (constraints["elective_credits"] is None and constraints["major_credits"] is None and 
                (latest_message.strip().isdigit() or re.match(r'^\d+학점$', latest_message.strip()))):
            num_value = extract_number(latest_message)
            logger.warning(f"단일 숫자 입력인데 처리되지 않음: {num_value}, 마지막 봇 메시지 맥락 확인")
            
            # 봇 히스토리 확인
            bot_history = [e for e in tracker.events if e.get('event') == 'bot' and e.get('text')][-3:]
            for bot_event in reversed(bot_history):
                bot_text = bot_event.get('text', '')
                logger.debug(f"봇 히스토리 메시지: '{bot_text}'")
                
                if "교양" in bot_text and "학점" in bot_text:
                    logger.info(f"봇 히스토리에서 교양 학점 질문 발견, {num_value}로 교양 학점 설정")
                    constraints["elective_credits"] = num_value
                    events.append(SlotSet("elective_credits_slot", str(num_value)))
                    break
                elif "전공" in bot_text and "학점" in bot_text:
                    logger.info(f"봇 히스토리에서 전공 학점 질문 발견, {num_value}로 전공 학점 설정")
                    constraints["major_credits"] = num_value
                    events.append(SlotSet("major_credits_slot", str(num_value)))
                    break
        
        logger.info(f"최종 추출 결과: {constraints}")
        return constraints, events