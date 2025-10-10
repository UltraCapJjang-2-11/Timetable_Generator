"""
시간표 생성 관련 설정 및 상수
모든 매직 넘버와 설정값을 중앙 집중식으로 관리
"""

# ============================================================================
# 학기 정보
# ============================================================================
CURRENT_YEAR = 2025
CURRENT_TERM = "1학기"

# ============================================================================
# 학점 제약
# ============================================================================
MIN_CREDITS = 0
MAX_CREDITS = 30
MAX_MAJOR_CREDITS = 24
MAX_ELECTIVE_CREDITS = 24

# 학점 기본값
DEFAULT_TOTAL_CREDITS = 18
DEFAULT_MAJOR_CREDITS = 9
DEFAULT_ELECTIVE_CREDITS = 9

# ============================================================================
# 건물 거리 및 이동 시간
# ============================================================================
DEFAULT_WALKING_TIME = 5  # 건물 간 기본 이동 시간 (분)
MAX_WALKING_TIME_NO_LIMIT = 20  # "상관없음" 옵션 값 (분)

# ============================================================================
# 점수 가중치 (목적함수)
# ============================================================================
class ScoringWeights:
    """시간표 생성 시 사용되는 점수 가중치"""

    # 목적함수 가중치 (최종 점수 계산) - 사용자 선호 중심으로 재조정
    GRADUATION_PRIORITY_WEIGHT = 1000  # 졸업요건 충족도
    PREFERENCE_WEIGHT = 3500           # 사용자 선호도 (2500 -> 3500, 최우선)
    RATING_WEIGHT = 800                # 강의 평점 (2000 -> 800, 대폭 감소)
    COMPACTNESS_WEIGHT = 2500          # 시간표 밀집도 (1500 -> 2500, 대폭 강화)
    REQUIRED_COURSE_WEIGHT = 1000      # 전공필수 우선순위
    ELECTIVE_COURSE_WEIGHT = 600       # 전공선택 우선순위
    GENERAL_CATEGORY_BONUS_WEIGHT = 500  # 교양 카테고리 충족 보너스 (신규)

    # 선호도 점수 (개별 항목)
    PREFERRED_INSTRUCTOR_BONUS = 100   # 선호 교수 보너스
    AVOIDED_INSTRUCTOR_PENALTY = -200  # 기피 교수 패널티
    PREFERRED_COURSE_BONUS = 100       # 선호 과목 보너스
    AVOIDED_COURSE_PENALTY = -200      # 기피 과목 패널티
    TIME_PREFERENCE_BONUS = 100        # 시간대 선호 보너스 (최대)
    TAG_MATCH_BONUS = 20               # 교양 태그 매칭 보너스
    TAG_MISMATCH_PENALTY = -10         # 교양 태그 불일치 패널티

    # 졸업요건 점수
    GRADUATION_REQUIREMENT_MULTIPLIER = 10  # 부족 학점 * 10
    GRADUATION_REQUIREMENT_MAX = 100        # 최대 점수
    MAJOR_REQUIRED_BONUS = 30               # 전공필수 추가 가중치

    # 교양 과목 초과 학점 패널티
    GENERAL_EXCESS_CREDIT_PENALTY = 30  # 초과 학점당 패널티

    # 평점 점수 (강의평) - 영향력 감소
    RATING_4_5_PLUS = 50    # 평점 4.5 이상 (100 -> 50)
    RATING_4_0_PLUS = 40    # 평점 4.0 이상 (75 -> 40)
    RATING_3_5_PLUS = 25    # 평점 3.5 이상 (50 -> 25)
    RATING_3_0_PLUS = 15    # 평점 3.0 이상 (25 -> 15)
    RATING_2_0_TO_3_0 = -15    # 평점 2.0~3.0 (페널티) (-25 -> -15)
    RATING_1_5_TO_2_0 = -25    # 평점 1.5~2.0 (페널티) (-50 -> -25)
    RATING_BELOW_1_5 = -50     # 평점 1.5 미만 (강한 페널티) (-100 -> -50)
    RATING_BELOW_3_0 = 0    # 평점 3.0 미만 (기존 호환성용, deprecated)

    # 밀집도 보너스 (대폭 강화)
    COMPACTNESS_BASE_BONUS = 500        # 연속 수업 보너스 (300 -> 500)
    COMPACTNESS_GAP_PENALTY = 200       # 공강시간당 패널티 (100 -> 200)

    # 시간대 선호도 (오전/오후) - 대폭 강화
    TIME_SLOT_PREFERENCE_BONUS = 100    # 선호 시간대 보너스 (50 -> 100)
    MORNING_PREFERENCE_BONUS = 500      # 오전 선호 보너스 (300 -> 500)
    AFTERNOON_PREFERENCE_BONUS = 500    # 오후 선호 보너스 (300 -> 500)
    PURE_TIME_PREFERENCE_BONUS = 200    # 순수 오전/오후 과목 추가 보너스 (100 -> 200)

    # 교양 과목 시간대 선호도 (매우 강력)
    GENERAL_TIME_MISMATCH_PENALTY = -1000   # 교양 과목 시간대 불일치 강한 패널티
    GENERAL_TIME_MATCH_BONUS = 300          # 교양 과목 시간대 일치 보너스

# ============================================================================
# 시간 관련 상수
# ============================================================================
CLASS_START_HOUR = 8        # 수업 시작 시간 (08:00)
MORNING_END_HOUR = 12       # 오전 종료 시간 (12:00)
AFTERNOON_START_HOUR = 13   # 오후 시작 시간 (13:00)
CLASS_END_HOUR = 18         # 수업 종료 시간 (18:00)

# ============================================================================
# 솔버 파라미터
# ============================================================================
class SolverParameters:
    """CP-SAT 솔버 파라미터"""

    # Phase 1: 최적해 찾기
    PHASE1_MAX_TIME = 5             # 최대 실행 시간 (초)
    PHASE1_NUM_WORKERS = 4          # 병렬 처리 워커 수
    PHASE1_LINEARIZATION_LEVEL = 2  # 선형화 레벨

    # Phase 2: 다양한 해 찾기
    PHASE2_MAX_TIME = 1             # 각 해당 최대 시간 (초)
    PHASE2_NUM_WORKERS = 4          # 병렬 처리 워커 수
    PHASE2_MAX_SOLUTIONS = 100      # 최대 해 개수 (1500 -> 100, 성능 향상)

# ============================================================================
# 필터링 관련 상수
# ============================================================================
EXCLUDE_TIME_SLOT = "00"           # 제외할 시간 슬롯
EXCLUDE_LOCATION_KEYWORD = "가상강의실"  # 제외할 강의실 키워드
GENERAL_EDUCATION_TARGET_YEAR = "전학년"  # 교양 과목 대상 학년

# ============================================================================
# 학과 관련 설정
# ============================================================================
# 소프트웨어 관련 학과 그룹 (ID)
SOFTWARE_RELATED_DEPT_IDS = {3, 9}  # 소프트웨어학과(3), 소프트웨어학부(9)

# 관련 학과 그룹 정의
RELATED_DEPT_GROUPS = [
    SOFTWARE_RELATED_DEPT_IDS,  # 소프트웨어 관련
    # 필요시 다른 그룹 추가 가능
]

# ============================================================================
# 카테고리 관련
# ============================================================================
MAJOR_CATEGORIES = ["전공필수", "전공선택"]
GENERAL_EDUCATION_CATEGORIES = ["교양"]

# 교양 세부 카테고리 매핑
GENERAL_EDUCATION_SUBCATEGORIES = [
    "개신기초교양",
    "일반교양",
    "자연이공계기초과학",
    "확대교양",
]

# ============================================================================
# 교양 과목 태그 필터
# ============================================================================
TAG_FILTERS = {
    '#조별과제가 없는': lambda course_name: '팀' not in course_name and '조별' not in course_name,
    '#과제가 적은': lambda course_name: '실습' not in course_name,
    '#시험이 쉬운': lambda course_name: '심화' not in course_name and '고급' not in course_name,
    '#출석 체크가 없는': lambda course_name: '실습' not in course_name and '실험' not in course_name,
    '#온라인 강의': lambda course_name: '온라인' in course_name or '사이버' in course_name,
    '#토론이 많은': lambda course_name: '토론' in course_name or '세미나' in course_name,
    '#실습이 많은': lambda course_name: '실습' in course_name or '실험' in course_name,
    '#이론 중심': lambda course_name: '이론' in course_name or '개론' in course_name
}

# ============================================================================
# 디버그 설정
# ============================================================================
DEBUG_MODE = True  # 디버그 모드 (나중에 settings.py에서 가져오도록 변경 가능)
DEBUG_PRINT_LIMIT = 5  # 디버그 출력 제한 (예: 처음 5개만)

# ============================================================================
# 추천 레벨 설정
# ============================================================================
RECOMMENDATION_LEVELS = {
    'excellent': ('★★★★★', 3000),    # 3000점 초과
    'great': ('★★★★', 1500),          # 1500점 초과
    'good': ('★★★', 0),               # 0점 초과
    'fair': ('★★', -1000),            # -1000점 이상
    'poor': ('★', float('-inf'))      # 그 외
}

# ============================================================================
# 유효성 검증 메시지
# ============================================================================
class ValidationMessages:
    """유효성 검증 관련 메시지"""

    INVALID_CREDITS = "학점 파라미터가 올바르지 않습니다."
    NO_SOLUTION_FOUND = "해결책을 찾지 못했습니다."
    NO_TIMETABLE_FOUND = "조건에 맞는 시간표를 찾지 못했습니다. 조건을 변경해보세요."
    SUCCESS_MESSAGE_TEMPLATE = "선호도 순으로 정렬된 {count}개의 시간표를 찾았습니다."

    # 학점 범위 경고
    ABNORMAL_TOTAL_CREDITS = "비정상적인 총 학점 요청"
    ABNORMAL_MAJOR_CREDITS = "비정상적인 전공 학점 요청"
    ABNORMAL_ELECTIVE_CREDITS = "비정상적인 교양 학점 요청"
    CREDITS_ADJUSTED = "학점 조정됨 (초과) - 전공: {major}, 교양: {elective}"
    ACTUAL_CREDITS_ADJUSTED = "실제 목표 학점 조정 - 요청: {requested}, 실제: {actual}"
