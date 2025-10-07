"""
공통 유틸리티 함수들
시간표 생성 및 강의 관리에 사용되는 헬퍼 함수들을 모아놓은 모듈
"""

import json
import re
from typing import List, Set
from collections import defaultdict
from data_manager.services.course_filter_service import CourseFilterService
from data_manager.models import Department


def parse_time_slots(times_str: str, add_base_hour: bool = False) -> List[int]:
    """
    시간 문자열을 파싱하여 정수 리스트로 변환

    Args:
        times_str: 시간 문자열 (예: "02,03,04" 또는 "02, 03, 04")
        add_base_hour: True면 CLASS_START_HOUR(8)을 더함

    Returns:
        시간 슬롯 리스트 (예: [2,3,4] 또는 [10,11,12])
    """
    if not times_str:
        return []

    try:
        # 쉼표로 분리하고 공백 제거
        time_parts = times_str.split(',')
        result = []

        for t in time_parts:
            t = t.strip()
            if t.isdigit():
                time_val = int(t)
                if add_base_hour:
                    time_val += 8  # CLASS_START_HOUR
                result.append(time_val)

        return result
    except (ValueError, AttributeError):
        return []


def parse_time_slots_to_set(times_str: str) -> Set[str]:
    """
    시간 문자열을 파싱하여 문자열 집합으로 변환 (시간 충돌 체크용)

    Args:
        times_str: 시간 문자열 (예: "02,03,04")

    Returns:
        시간 슬롯 문자열 집합 (예: {'02','03','04'})
    """
    if not times_str:
        return set()

    try:
        return set(t.strip() for t in times_str.split(',') if t.strip())
    except (ValueError, AttributeError):
        return set()


class DummyObj:
    """CP-SAT 조건 처리용 더미 객체"""
    def __init__(self, data):
        self.__dict__.update(data)


def get_effective_general_category(course) -> str:
    """
    Courses.category (FK)로부터 Category 트리를 타고 올라가
    '개신기초교양', '일반교양', '자연이공계기초', '확대교양' 중
    하나의 표준 키를 반환한다. 매핑이 없으면 빈 문자열.
    """
    mapping = {
        "개신기초교양": "개신기초교양",
        "일반교양": "일반교양",
        "자연이공계기초과학": "자연이공계기초과학",
        "확대교양": "확대교양",
    }

    cat = getattr(course, "category", None)
    while cat:
        name = cat.category_name
        if name in mapping:
            return mapping[name]
        cat = cat.parent_category  # 위로 한 단계
    return ""


def get_simplified_category_name(course):
    """
    강의의 카테고리를 상위 분류로 통일하는 함수
    교양 과목의 경우 level 2(세부분류)를 level 1(상위분류)로 변경
    예: "인간과문화" -> "일반교양"
    """
    if not course.category:
        return None
    
    category = course.category
    
    # 카테고리 레벨이 2이고, 부모의 부모가 "교양"인 경우
    if (category.category_level == 2 and 
        category.parent_category and 
        category.parent_category.parent_category and 
        category.parent_category.parent_category.category_name == "교양"):
        # 부모 카테고리(level 1)의 이름을 반환
        return category.parent_category.category_name
    
    # 그 외의 경우는 원래 카테고리 이름 반환
    return category.category_name


def extract_missing_required_major_courses(user_dept_id, completed_courses):
    """
    사용자 전공(dept_id)에 해당하는 전공필수 강좌 중,
    이미 이수한 과목(completed_courses 집합)에 포함되지 않은 고유 course_name(대문자 기준)들을 반환.
    """
    svc = CourseFilterService()
    user_dept_name = Department.objects.get(pk=user_dept_id)  # 학과(학부) 이름 조회

    missing_courses = set()
    required_courses = svc.course_search(category_name='전공필수', dept_name=user_dept_name)
    for course in required_courses:
        cname = course.course_name.strip().upper()
        if cname not in completed_courses:
            missing_courses.add(cname)
    return missing_courses


def apply_time_constraints(candidate_data, only_ranges, avoid_times, avoid_ranges, specific_avoid_times=None, specific_avoid_time_ranges=None):
    """
    시간 제약조건을 적용하여 후보 강좌 목록을 필터링합니다.
    
    Args:
        candidate_data: 후보 강좌 데이터 리스트
        only_ranges: 허용할 시간대 목록
        avoid_times: 피해야 할 특정 시간 목록
        avoid_ranges: 피해야 할 시간대 목록
        specific_avoid_times: 특정 요일+시간 회피 목록
        specific_avoid_time_ranges: 특정 요일+시간범위 회피 목록
    
    Returns:
        필터링된 후보 강좌 데이터 리스트
    """
    if specific_avoid_times is None:
        specific_avoid_times = []
    if specific_avoid_time_ranges is None:
        specific_avoid_time_ranges = []
    
    # 1) only_time_ranges 적용 — 있으면 이 범위 **외** 과목 제거
    if only_ranges:
        filtered = []
        for data in candidate_data:
            ok = True
            for sched in data['schedule']:
                # times: "02,03,04" → [10,11,12]
                hours = parse_time_slots(sched['times'], add_base_hour=True)
                if not any(
                    sched['day'] in r['days']
                    and all(h >= r['start_hour'] and
                            ('end_hour' not in r or h < r['end_hour'])
                        for h in hours)
                    for r in only_ranges
                ):
                    ok = False
                    break
            if ok:
                filtered.append(data)
        candidate_data = filtered

    # 2) avoid_times / avoid_time_ranges 적용 — 걸리면 제거
    if avoid_times or avoid_ranges:
        filtered = []
        for data in candidate_data:
            bad = False
            for sched in data['schedule']:
                hours = parse_time_slots(sched['times'], add_base_hour=True)
                # (1) 단일 시각 회피
                if any(obj['day']==sched['day'] and h==obj['hour'] 
                       for obj in avoid_times for h in hours):
                    bad = True
                    break
                # (2) 범위 회피
                if any(
                    sched['day'] in r['days']
                    and any(h >= r['start_hour'] and
                            ('end_hour' not in r or h < r['end_hour'])
                        for h in hours)
                    for r in avoid_ranges
                ):
                    bad = True
                    break
            if not bad:
                filtered.append(data)
        candidate_data = filtered

    # 3) specific_avoid_times / specific_avoid_time_ranges 적용 — 특정 요일+시간 회피
    if specific_avoid_times or specific_avoid_time_ranges:
        filtered = []
        for data in candidate_data:
            bad = False
            for sched in data['schedule']:
                hours = parse_time_slots(sched['times'], add_base_hour=True)
                
                # (1) 특정 요일+시간 회피
                if any(obj['day']==sched['day'] and h==obj['hour'] 
                       for obj in specific_avoid_times for h in hours):
                    bad = True
                    print(f"DEBUG: 특정 시간 회피로 과목 제외 - {data.get('course_name', 'Unknown')} ({sched['day']}요일 {hours}시)")
                    break
                
                # (2) 특정 요일+시간범위 회피
                if any(
                    obj['day']==sched['day']
                    and any(h >= obj['start_hour'] and h < obj['end_hour']
                        for h in hours)
                    for obj in specific_avoid_time_ranges
                ):
                    bad = True
                    print(f"DEBUG: 특정 시간범위 회피로 과목 제외 - {data.get('course_name', 'Unknown')} ({sched['day']}요일 {hours}시)")
                    break
            if not bad:
                filtered.append(data)
        candidate_data = filtered

    return candidate_data


def extract_number(text):
    """텍스트에서 숫자를 추출합니다."""
    if not text:
        return None
    
    # 숫자 추출 정규식
    numbers = re.findall(r'\d+', text)
    if numbers:
        return int(numbers[0])
    return None


def get_korean_day_abbr(day_text):
    """한글 요일 전체 이름을 약자로 변환합니다."""
    day_text = str(day_text).strip().lower()
    mapping = {
        "월요일": "월", "화요일": "화", "수요일": "수", "목요일": "목", "금요일": "금",
        "월": "월", "화": "화", "수": "수", "목": "목", "금": "금",
        "월공강": "월", "화공강": "화", "수공강": "수", "목공강": "목", "금공강": "금",
    }
    
    for key, value in mapping.items():
        if key in day_text:
            return value
    return day_text


def parse_time_range(time_text):
    """시간대 텍스트를 시간 범위로 변환합니다."""
    if "오전" in time_text:
        return {"start_hour": 9, "end_hour": 12}
    elif "오후" in time_text:
        return {"start_hour": 13, "end_hour": 18}
    return None 