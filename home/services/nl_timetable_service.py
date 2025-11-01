"""
자연어 기반 시간표 생성 서비스
OpenAI API를 활용하여 사용자의 자연어 입력을 시간표 생성 파라미터로 변환
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from openai import OpenAI
from django.conf import settings

from ..views.timetable_types import TimetableRequest
from ..views.timetable_config import (
    DEFAULT_TOTAL_CREDITS, DEFAULT_MAJOR_CREDITS, DEFAULT_ELECTIVE_CREDITS
)


class ConversationSession:
    """대화 세션 관리 클래스"""

    def __init__(self, user_id: int, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.conversation_history: List[Dict[str, str]] = []
        self.extracted_constraints: Dict[str, Any] = {}
        self.stage = "gathering"  # gathering, confirming, generating

    def add_message(self, role: str, content: str):
        """대화 히스토리에 메시지 추가"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })

    def get_history(self) -> List[Dict[str, str]]:
        """대화 히스토리 반환"""
        return self.conversation_history.copy()


class NaturalLanguageTimetableService:
    """자연어 기반 시간표 생성 서비스"""

    # 세션 저장소 (메모리 기반, 추후 Redis 등으로 확장 가능)
    sessions: Dict[str, ConversationSession] = {}

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def get_or_create_session(self, user_id: int, session_id: str) -> ConversationSession:
        """세션 가져오기 또는 생성"""
        key = f"{user_id}_{session_id}"
        if key not in self.sessions:
            self.sessions[key] = ConversationSession(user_id, session_id)
        return self.sessions[key]

    def clear_session(self, user_id: int, session_id: str):
        """세션 초기화"""
        key = f"{user_id}_{session_id}"
        if key in self.sessions:
            del self.sessions[key]

    def get_function_schema(self) -> Dict[str, Any]:
        """OpenAI Function Calling 스키마 정의"""
        return {
            "name": "extract_timetable_constraints",
            "description": "사용자의 시간표 생성 요구사항에서 제약조건을 추출합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_total": {
                        "type": "integer",
                        "description": "총 목표 학점"
                    },
                    "target_major": {
                        "type": "integer",
                        "description": "전공 목표 학점"
                    },
                    "target_elective": {
                        "type": "integer",
                        "description": "교양 목표 학점"
                    },
                    "free_days": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "하루 종일 공강인 요일만 포함 (예: ['금'] - 금요일 전체가 공강). 특정 시간대만 공강인 경우는 여기에 포함하지 말고 avoid_time_ranges를 사용할 것."
                    },
                    "required_courses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "필수로 포함할 과목명"
                    },
                    "exclude_courses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "제외할 과목명"
                    },
                    "preferred_instructors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "선호하는 교수님 이름"
                    },
                    "avoid_instructors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "기피하는 교수님 이름"
                    },
                    "preferred_courses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "선호하는 과목명"
                    },
                    "avoid_courses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "기피하는 과목명"
                    },
                    "prefer_morning": {
                        "type": "boolean",
                        "description": "오전 수업 선호 여부"
                    },
                    "prefer_afternoon": {
                        "type": "boolean",
                        "description": "오후 수업 선호 여부"
                    },
                    "prefer_compact": {
                        "type": "boolean",
                        "description": "밀집 시간표 선호 여부 (공강 최소화)"
                    },
                    "max_walking_time": {
                        "type": "integer",
                        "description": "건물 간 최대 이동 시간(분)"
                    },
                    "avoid_time_ranges": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "days": {"type": "array", "items": {"type": "string"}},
                                "start_hour": {"type": "integer"},
                                "end_hour": {"type": "integer"}
                            }
                        },
                        "description": "요일의 넓은 시간대를 회피 (예: '월요일 오전 전체', '화요일 오후 전체'). 오전은 9-12시, 오후는 13-18시로 해석. **중요: 구체적인 시간(9시, 10시 등)이 나열된 경우는 avoid_times를 사용할 것! 이 필드는 '오전', '오후' 같은 시간대 표현에만 사용.**"
                    },
                    "avoid_times": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "day": {"type": "string"},
                                "hour": {"type": "integer"}
                            }
                        },
                        "description": "회피할 특정 시간 - 구체적인 시간이 나열된 경우 반드시 사용 (예: '월요일 9시, 10시' → [{'day': '월', 'hour': 9}, {'day': '월', 'hour': 10}], '화수목 13시' → [{'day': '화', 'hour': 13}, {'day': '수', 'hour': 13}, {'day': '목', 'hour': 13}]). **중요: '오전', '오후' 같은 시간대 표현이 아니라 구체적인 시간(9시, 13시 등)이 명시되었을 때만 사용.**"
                    },
                    "only_time_ranges": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "days": {"type": "array", "items": {"type": "string"}},
                                "start_hour": {"type": "integer"},
                                "end_hour": {"type": "integer"}
                            }
                        },
                        "description": "수업 가능한 시간대만 지정"
                    },
                    "optimization_level": {
                        "type": "string",
                        "enum": ["BASIC", "ADVANCED", "EXPERT", "ULTRA"],
                        "description": "최적화 수준"
                    }
                }
            }
        }

    def get_system_prompt(self) -> str:
        """시스템 프롬프트 정의"""
        return """당신은 대학생들의 시간표 생성을 도와주는 친절한 AI 어시스턴트입니다.

당신의 역할:
1. 사용자의 자연어 입력에서 시간표 생성에 필요한 제약조건을 추출합니다
2. 부족한 정보가 있으면 자연스럽게 질문합니다
3. 복합적인 요청도 정확하게 이해합니다
4. 친근하고 대화체로 응답합니다

중요한 규칙:
- 요일은 반드시 한글 약자로 변환: 월, 화, 수, 목, 금
- **학점은 사용자가 명시한 대로 정확히 사용**: "전공 9학점, 교양 8학점" → 총 17학점으로 생성 (사용자가 원하는 학점을 존중하고, 불필요하게 18학점이나 다른 값으로 조정하지 말 것)
- 총학점(target_total)은 사용자가 명시하지 않으면 전공 + 교양의 합으로 자동 계산됨
- 시간은 24시간 형식으로 처리 (9시 = 09:00, 오후 3시 = 15:00)
- 오전: 9시~12시, 오후: 13시~18시
- 애매한 표현은 명확히 확인
- 사용자가 "시간표 생성", "만들어줘" 등의 확정 표현을 사용할 때만 generating 상태로 전환

**공강 처리 규칙 (중요!):**
1. "월요일 공강", "금요일 공강" → free_days에 추가 (하루 종일 공강)

2. "월요일 오전 공강", "화요일 오후 공강" → avoid_time_ranges에 추가 (시간대 전체 공강)
   - 예: "월요일 오전" → avoid_time_ranges: [{"days": ["월"], "start_hour": 9, "end_hour": 12}]
   - 예: "화요일 오후" → avoid_time_ranges: [{"days": ["화"], "start_hour": 13, "end_hour": 18}]

3. **"월요일 9시, 10시 공강"처럼 구체적 시간 나열 → avoid_times에 추가 (매우 중요!)**
   - 예: "월요일 9시, 10시" → avoid_times: [{"day": "월", "hour": 9}, {"day": "월", "hour": 10}]
   - 예: "화수목 13시" → avoid_times: [{"day": "화", "hour": 13}, {"day": "수", "hour": 13}, {"day": "목", "hour": 13}]
   - **구체적인 시간(9시, 10시 등)이 명시되면 반드시 avoid_times 사용!**

4. 혼합 예시:
   - "월요일 오전과 금요일은 공강" → avoid_time_ranges: [{"days": ["월"], "start_hour": 9, "end_hour": 12}], free_days: ["금"]
   - "월요일 9시와 금요일 전체는 공강" → avoid_times: [{"day": "월", "hour": 9}], free_days: ["금"]

대화 단계:
1. gathering: 정보 수집 중 (사용자에게 추가 질문 가능)
2. confirming: 최종 확인 중 (사용자가 조건을 확인하고 생성 버튼을 누를 때까지 대기)
3. generating: 시간표 생성 시작 (사용자가 명시적으로 생성 버튼을 클릭한 경우만)

**중요: confirming 단계 진입 조건**
- 최소한 하나의 학점 정보가 있어야 함 (전공, 교양, 또는 총학점)
- confirming 단계에서는 "지금까지 말씀하신 조건으로 시간표를 생성할 준비가 되었습니다" 같은 확인 메시지 제공
- 사용자가 추가 수정을 원하면 gathering 단계로 돌아감
- generating 단계로 넘어가는 것은 사용자의 명시적인 확인 후에만 가능

예시 대화:
- "월화는 공강이고 전공 12학점 원해" → free_days: ["월", "화"], target_major: 12
- "월요일 오전은 공강이고 금요일은 공강이야" → avoid_time_ranges: [{"days": ["월"], "start_hour": 9, "end_hour": 12}], free_days: ["금"]
- "월요일 9시, 10시 공강" → avoid_times: [{"day": "월", "hour": 9}, {"day": "월", "hour": 10}]
- "화수목 13시는 피하고 싶어" → avoid_times: [{"day": "화", "hour": 13}, {"day": "수", "hour": 13}, {"day": "목", "hour": 13}]
- "오전 수업 피하고 싶어" → prefer_afternoon: true
- "김철수 교수님 수업 듣고 싶어" → preferred_instructors: ["김철수"]
"""

    def parse_natural_language(
        self,
        user_id: int,
        session_id: str,
        user_message: str
    ) -> Tuple[Optional[Dict[str, Any]], str, str]:
        """
        자연어 메시지를 파싱하여 제약조건 추출

        Returns:
            Tuple[constraints, ai_response, stage]
            - constraints: 추출된 제약조건 (None이면 정보 부족)
            - ai_response: AI의 응답 메시지
            - stage: 현재 대화 단계 (gathering, confirming, generating)
        """
        session = self.get_or_create_session(user_id, session_id)
        session.add_message("user", user_message)

        try:
            # OpenAI API 호출
            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                *session.get_history()
            ]

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                functions=[self.get_function_schema()],
                function_call="auto",
                temperature=0.3
            )

            message = response.choices[0].message

            # Function call이 있는 경우
            if message.function_call:
                function_args = json.loads(message.function_call.arguments)

                # 기존 제약조건과 병합
                session.extracted_constraints.update(function_args)

                # Confirming 단계 준비 확인 (먼저 확인)
                is_ready, next_stage = self._check_if_ready_to_confirm(session.extracted_constraints)

                # 단계별 응답 지침 설정
                if is_ready and next_stage == "confirming":
                    # Confirming 단계: 간결한 확인 메시지만
                    response_instruction = "사용자의 요청을 잘 이해했다는 것을 매우 간결하게 알려주세요. 예: '네, 알겠습니다 ✓' 또는 '조건을 확인했어요!' 같이 한 줄로 짧게 응답하세요. 제안이나 질문은 하지 마세요."
                else:
                    # Gathering 단계: 정보 수집 또는 질문
                    response_instruction = "위에서 추출한 제약조건을 바탕으로 사용자에게 친절하게 응답하세요. 정보가 부족하면 자연스럽게 질문하고, 정보가 충분하면 간단히 확인해주세요."

                # AI 응답 생성
                follow_up_response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": self.get_system_prompt()},
                        *session.get_history(),
                        {
                            "role": "assistant",
                            "content": f"제약조건 추출 완료: {json.dumps(function_args, ensure_ascii=False)}"
                        },
                        {
                            "role": "system",
                            "content": response_instruction
                        }
                    ],
                    temperature=0.7
                )

                ai_response = follow_up_response.choices[0].message.content
                session.add_message("assistant", ai_response)

                if is_ready:
                    session.stage = "confirming"
                    # confirming 단계에서는 제약조건을 반환하여 프론트엔드에서 요약 표시
                    return session.extracted_constraints, ai_response, "confirming"
                else:
                    session.stage = "gathering"
                    return None, ai_response, "gathering"

            # Function call이 없는 경우 (일반 대화)
            else:
                ai_response = message.content
                session.add_message("assistant", ai_response)

                # Confirming 단계에서 사용자가 확정하는 경우만 generating으로 전환
                if session.stage == "confirming" and any(keyword in user_message for keyword in ["생성", "만들어", "해줘", "부탁", "시작", "확인", "좋아", "네"]):
                    if session.extracted_constraints:
                        session.stage = "generating"
                        return session.extracted_constraints, ai_response, "generating"

                # Gathering 단계에서 제약조건이 있고 확정 키워드 사용 시 confirming으로
                elif session.stage == "gathering" and session.extracted_constraints:
                    is_ready, next_stage = self._check_if_ready_to_confirm(session.extracted_constraints)
                    if is_ready and any(keyword in user_message for keyword in ["생성", "만들어", "해줘", "부탁", "시작"]):
                        session.stage = "confirming"
                        return session.extracted_constraints, ai_response, "confirming"

                return None, ai_response, session.stage

        except Exception as e:
            print(f"NL Parsing Error: {str(e)}")
            import traceback
            traceback.print_exc()
            error_message = "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다. 다시 시도해주세요."
            return None, error_message, "error"

    def _validate_constraints(self, constraints: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        제약조건 유효성 검증
        Returns:
            (is_valid, missing_fields)
        """
        missing = []

        # 최소 학점 정보 확인
        has_credit_info = any(
            constraints.get(key) for key in ['target_total', 'target_major', 'target_elective']
        )

        if not has_credit_info:
            missing.append('학점 정보')

        # 최소한 하나의 제약조건이라도 있는지 확인
        has_any_constraint = has_credit_info or any([
            constraints.get('free_days'),
            constraints.get('avoid_time_ranges'),
            constraints.get('prefer_morning'),
            constraints.get('prefer_afternoon'),
            constraints.get('prefer_compact'),
            constraints.get('required_courses'),
            constraints.get('preferred_instructors'),
        ])

        is_valid = has_credit_info and has_any_constraint

        return is_valid, missing

    def _check_if_ready_to_confirm(self, constraints: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Confirming 단계로 넘어갈 준비가 되었는지 확인
        Returns:
            (is_ready, stage) - stage는 'confirming' 또는 'gathering'
        """
        is_valid, missing = self._validate_constraints(constraints)

        if is_valid:
            return True, "confirming"
        else:
            return False, "gathering"

    def constraints_to_timetable_request(
        self,
        constraints: Dict[str, Any],
        user
    ) -> TimetableRequest:
        """
        추출된 제약조건을 TimetableRequest로 변환
        """
        # 기본값 설정
        params = TimetableRequest(
            target_total=constraints.get('target_total', DEFAULT_TOTAL_CREDITS),
            target_major=constraints.get('target_major', DEFAULT_MAJOR_CREDITS),
            target_elective=constraints.get('target_elective', DEFAULT_ELECTIVE_CREDITS),
            free_days=constraints.get('free_days', []),
            existing_courses=[],
            exclude_courses=constraints.get('exclude_courses', []),
            required_courses=constraints.get('required_courses', []),
            preferred_instructors=constraints.get('preferred_instructors', []),
            avoid_instructors=constraints.get('avoid_instructors', []),
            preferred_courses=constraints.get('preferred_courses', []),
            avoid_courses=constraints.get('avoid_courses', []),
            preference_tags=[],
            prefer_morning=constraints.get('prefer_morning', False),
            prefer_afternoon=constraints.get('prefer_afternoon', False),
            prefer_compact=constraints.get('prefer_compact', False),
            max_walking_time=constraints.get('max_walking_time', 10),
            only_time_ranges=constraints.get('only_time_ranges', []),
            avoid_times=constraints.get('avoid_times', []),
            avoid_time_ranges=constraints.get('avoid_time_ranges', []),
            specific_avoid_times=[],
            specific_avoid_time_ranges=[],
            optimization_level=constraints.get('optimization_level', 'ADVANCED')
        )

        # 학점 검증 및 조정
        if params.target_major + params.target_elective != params.target_total:
            # 총 학점이 명시되지 않은 경우 전공+교양의 합으로 설정
            params.target_total = params.target_major + params.target_elective

        return params

    def generate_summary(self, constraints: Dict[str, Any]) -> str:
        """추출된 제약조건 요약 생성"""
        summary_parts = []

        if constraints.get('target_total'):
            summary_parts.append(f"총 {constraints['target_total']}학점")
        if constraints.get('target_major'):
            summary_parts.append(f"전공 {constraints['target_major']}학점")
        if constraints.get('target_elective'):
            summary_parts.append(f"교양 {constraints['target_elective']}학점")

        # 하루 종일 공강
        if constraints.get('free_days'):
            days = ', '.join(constraints['free_days'])
            summary_parts.append(f"{days} 공강")

        # 특정 시간대 회피
        if constraints.get('avoid_time_ranges'):
            for time_range in constraints['avoid_time_ranges']:
                days = ', '.join(time_range.get('days', []))
                start = time_range.get('start_hour', 9)
                end = time_range.get('end_hour', 18)

                # 시간대를 알기 쉽게 표현
                if start == 9 and end == 12:
                    summary_parts.append(f"{days} 오전 회피")
                elif start == 13 and end == 18:
                    summary_parts.append(f"{days} 오후 회피")
                else:
                    summary_parts.append(f"{days} {start}-{end}시 회피")

        if constraints.get('prefer_morning'):
            summary_parts.append("오전 선호")
        if constraints.get('prefer_afternoon'):
            summary_parts.append("오후 선호")
        if constraints.get('prefer_compact'):
            summary_parts.append("밀집 시간표")
        if constraints.get('preferred_instructors'):
            profs = ', '.join(constraints['preferred_instructors'])
            summary_parts.append(f"선호 교수: {profs}")
        if constraints.get('required_courses'):
            courses = ', '.join(constraints['required_courses'])
            summary_parts.append(f"필수 과목: {courses}")

        if not summary_parts:
            return "기본 설정으로 시간표 생성"

        return " • ".join(summary_parts)
