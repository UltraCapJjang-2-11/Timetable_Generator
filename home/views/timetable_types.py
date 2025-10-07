"""
시간표 생성 관련 데이터 클래스 및 타입 정의
요청 파라미터, 후보 과목, 필터 등을 명확하게 정의
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any


# ============================================================================
# 요청 관련 데이터 클래스
# ============================================================================

@dataclass
class TimetableRequest:
    """시간표 생성 요청 파라미터"""

    # 학점 관련
    target_total: int = 18
    target_major: int = 9
    target_elective: int = 9

    # 공강 및 제외 과목
    free_days: List[str] = field(default_factory=list)
    existing_courses: List[int] = field(default_factory=list)
    exclude_courses: List[str] = field(default_factory=list)
    required_courses: List[str] = field(default_factory=list)

    # 선호도 관련
    preferred_instructors: List[str] = field(default_factory=list)
    avoid_instructors: List[str] = field(default_factory=list)
    preferred_courses: List[str] = field(default_factory=list)
    avoid_courses: List[str] = field(default_factory=list)

    # 교양 과목 태그
    preference_tags: List[str] = field(default_factory=list)

    # 시간대 선호
    prefer_morning: bool = False
    prefer_afternoon: bool = False
    prefer_compact: bool = False

    # 건물 거리
    max_walking_time: int = 10

    # 시간 제약 조건
    only_time_ranges: List[Dict[str, Any]] = field(default_factory=list)
    avoid_times: List[Dict[str, Any]] = field(default_factory=list)
    avoid_time_ranges: List[Dict[str, Any]] = field(default_factory=list)
    specific_avoid_times: List[Dict[str, Any]] = field(default_factory=list)
    specific_avoid_time_ranges: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class UserInfo:
    """사용자 정보"""

    user_id: int
    student_dept_id: Optional[int] = None
    dept_name: str = ""
    current_year: int = 3
    completed_courses: Set[str] = field(default_factory=set)
    missing_gen_sub: Dict[str, int] = field(default_factory=dict)
    graduation_progress: List[Any] = field(default_factory=list)


# ============================================================================
# 후보 과목 관련 데이터 클래스
# ============================================================================

@dataclass
class CourseScheduleInfo:
    """강의 스케줄 정보"""

    day: str
    times: str
    location: str


@dataclass
class CourseCandidate:
    """후보 과목 정보"""

    # 기본 정보
    course_id: int
    course_name: str
    course_code: str
    section: str
    credits: int
    target_year: str
    instructor_name: str
    capacity: int
    dept_name: str
    category: str
    semester: str
    location: str

    # 스케줄 정보
    schedules: List[CourseScheduleInfo] = field(default_factory=list)
    buildings: List[str] = field(default_factory=list)

    # 점수 관련
    graduation_priority: int = 0
    preference_score: int = 0
    rating_score: int = 0

    # 상태 플래그
    pre_added: bool = False
    is_same_year: bool = False

    # 교양 과목 세부 카테고리
    effective_category: Optional[str] = None


# ============================================================================
# 필터 관련 데이터 클래스
# ============================================================================

@dataclass
class FilterCriteria:
    """후보 과목 필터링 기준"""

    # 학과 및 학년
    student_dept_id: Optional[int] = None
    current_year: int = 3

    # 이수 과목
    completed_courses: Set[str] = field(default_factory=set)

    # 제외 과목
    exclude_names: List[str] = field(default_factory=list)

    # 공강 요일
    free_days: List[str] = field(default_factory=list)

    # 미리 추가된 과목
    pre_added_ids: List[int] = field(default_factory=list)

    # 교양 세부 이수 상태
    missing_gen_sub: Dict[str, int] = field(default_factory=dict)


@dataclass
class ScoreCriteria:
    """점수 계산 기준"""

    # 졸업요건 우선순위 맵
    priority_map: Dict[int, float] = field(default_factory=dict)

    # 선호 교수/과목
    preferred_instructors: List[str] = field(default_factory=list)
    avoid_instructors: List[str] = field(default_factory=list)
    preferred_courses: List[str] = field(default_factory=list)
    avoid_courses: List[str] = field(default_factory=list)

    # 교양 태그
    preference_tags: List[str] = field(default_factory=list)

    # 시간대 선호
    prefer_morning: bool = False
    prefer_afternoon: bool = False

    # 밀집도 선호 (공강 최소화)
    prefer_compact: bool = False

    # 교양 세부 이수 상태 (초과 학점 패널티용)
    missing_gen_sub: Dict[str, int] = field(default_factory=dict)

    # 평점 정보
    review_summaries: Dict[tuple, Any] = field(default_factory=dict)


# ============================================================================
# 모델 구성 관련 데이터 클래스
# ============================================================================

@dataclass
class ConstraintData:
    """제약 조건 데이터"""

    # 학점 제약
    target_total: int
    target_major: int
    target_elective: int

    # 교양 세부 카테고리별 상한
    missing_gen_sub: Dict[str, int] = field(default_factory=dict)

    # 건물 간 이동 시간
    max_walking_time: int = 10

    # 밀집도 선호
    prefer_compact: bool = False


# ============================================================================
# 해 관련 데이터 클래스
# ============================================================================

@dataclass
class TimetableSolution:
    """시간표 해"""

    courses: List[Dict[str, Any]]
    preference_score: int = 0
    matched_preferences: Dict[str, int] = field(default_factory=dict)
    recommendation_level: str = "★★★"


# ============================================================================
# 유틸리티 함수
# ============================================================================

def schedule_dict_to_dataclass(schedule_dict: Dict[str, str]) -> CourseScheduleInfo:
    """스케줄 딕셔너리를 데이터클래스로 변환"""
    return CourseScheduleInfo(
        day=schedule_dict.get('day', ''),
        times=schedule_dict.get('times', ''),
        location=schedule_dict.get('location', '')
    )


def candidate_dict_to_dataclass(candidate_dict: Dict[str, Any]) -> CourseCandidate:
    """후보 과목 딕셔너리를 데이터클래스로 변환"""
    schedules = [
        schedule_dict_to_dataclass(s) if isinstance(s, dict) else s
        for s in candidate_dict.get('schedule', [])
    ]

    return CourseCandidate(
        course_id=candidate_dict.get('id', 0),
        course_name=candidate_dict.get('course_name', ''),
        course_code=candidate_dict.get('course_code', ''),
        section=candidate_dict.get('section', ''),
        credits=candidate_dict.get('credit', 0),
        target_year=candidate_dict.get('year', ''),
        instructor_name=candidate_dict.get('instructor_name', ''),
        capacity=candidate_dict.get('capacity', 0),
        dept_name=candidate_dict.get('dept_name', ''),
        category=candidate_dict.get('category', ''),
        semester=candidate_dict.get('semester', ''),
        location=candidate_dict.get('location', ''),
        schedules=schedules,
        buildings=candidate_dict.get('buildings', []),
        graduation_priority=candidate_dict.get('graduation_priority', 0),
        preference_score=candidate_dict.get('preference_score', 0),
        rating_score=candidate_dict.get('rating_score', 0),
        pre_added=candidate_dict.get('pre_added', False),
        is_same_year=candidate_dict.get('is_same_year', False),
        effective_category=candidate_dict.get('effective_category')
    )


def candidate_dataclass_to_dict(candidate: CourseCandidate) -> Dict[str, Any]:
    """후보 과목 데이터클래스를 딕셔너리로 변환"""
    return {
        'id': candidate.course_id,
        'course_name': candidate.course_name,
        'course_code': candidate.course_code,
        'section': candidate.section,
        'credit': candidate.credits,
        'credits': candidate.credits,
        'year': candidate.target_year,
        'instructor_name': candidate.instructor_name,
        'capacity': candidate.capacity,
        'dept_name': candidate.dept_name,
        'category': candidate.category,
        'semester': candidate.semester,
        'schedule': [
            {'day': s.day, 'times': s.times, 'location': s.location}
            for s in candidate.schedules
        ],
        'location': candidate.location,
        'buildings': candidate.buildings,
        'graduation_priority': candidate.graduation_priority,
        'preference_score': candidate.preference_score,
        'rating_score': candidate.rating_score,
        'pre_added': candidate.pre_added,
        'is_same_year': candidate.is_same_year,
        'effective_category': candidate.effective_category
    }
