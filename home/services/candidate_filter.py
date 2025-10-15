"""
시간표 후보 과목 필터링 서비스
조건에 맞지 않는 과목들을 단계별로 필터링
"""

from typing import List, Dict, Any
from django.db.models import QuerySet
from django.db.models.functions import Upper

from data_manager.models import Courses
from data_manager.services.course_filter_service import CourseFilterService

from ..views.timetable_types import FilterCriteria, UserInfo
from ..views.timetable_config import (
    CURRENT_YEAR, CURRENT_TERM,
    EXCLUDE_TIME_SLOT, EXCLUDE_LOCATION_KEYWORD,
    GENERAL_EDUCATION_TARGET_YEAR,
    MAJOR_CATEGORIES,
    RELATED_DEPT_GROUPS,
    MORNING_END_HOUR,
    CLASS_START_HOUR
)
from ..utils import get_effective_general_category, get_simplified_category_name, parse_time_slots


class CandidateFilter:
    """후보 과목 필터링"""

    def __init__(self):
        self.service = CourseFilterService()

    def get_candidates(
        self,
        user_info: UserInfo,
        criteria: FilterCriteria
    ) -> List[Courses]:
        """
        조건에 맞는 후보 과목 조회 및 필터링

        Args:
            user_info: 사용자 정보
            criteria: 필터링 기준

        Returns:
            필터링된 후보 과목 리스트
        """
        # 1. 기본 후보 과목 조회
        candidate_qs = self._get_base_queryset(user_info, criteria)

        # 2. 단계별 필터링
        candidates = []
        for course in candidate_qs:
            # 제외 과목 필터
            if self._should_exclude_course(course, criteria):
                continue

            # 전공 과목 필터
            if course.category.category_name in MAJOR_CATEGORIES:
                if not self._is_valid_major_course(course, user_info, criteria):
                    continue

            # 기본 필터
            if not self._passes_basic_filters(course, criteria):
                continue

            # 교양 과목 필터
            if get_effective_general_category(course):
                if not self._is_valid_general_course(course, criteria):
                    continue

            candidates.append(course)

        print(f"DEBUG: 필터링 완료 - 후보 과목 {len(candidates)}개")
        return candidates

    def _get_base_queryset(
        self,
        user_info: UserInfo,
        criteria: FilterCriteria
    ) -> QuerySet:
        """기본 후보 과목 QuerySet 생성"""
        # 전공과 교양의 모든 하위 카테고리 포함
        candidate_qs = (
            self.service.course_search(year=CURRENT_YEAR, term=CURRENT_TERM, category_name='전공') |
            self.service.course_search(year=CURRENT_YEAR, term=CURRENT_TERM, category_name='교양')
        ).annotate(upper_course_name=Upper('course_name'))

        # 이미 이수한 과목 제외
        if criteria.completed_courses:
            candidate_qs = candidate_qs.exclude(
                upper_course_name__in=[name.upper() for name in criteria.completed_courses]
            )

        return candidate_qs

    def _should_exclude_course(
        self,
        course: Courses,
        criteria: FilterCriteria
    ) -> bool:
        """과목을 제외해야 하는지 확인"""
        if not criteria.exclude_names:
            return False

        course_id_str = str(course.course_id)

        for exclude_item in criteria.exclude_names:
            exclude_item_str = str(exclude_item).strip()

            # 과목 코드로 정확히 매칭
            if course_id_str == exclude_item_str:
                print(f"DEBUG: 과목 제외됨 (ID 매칭) - '{course.course_name}' (ID: {course.course_id})")
                return True

            # 과목명으로 매칭
            if not exclude_item_str.isdigit():
                course_name_lower = course.course_name.lower().strip()
                exclude_name_lower = exclude_item_str.lower().strip()
                if (course_name_lower == exclude_name_lower or
                    exclude_name_lower in course_name_lower or
                    course_name_lower in exclude_name_lower):
                    print(f"DEBUG: 과목 제외됨 (이름 매칭) - '{course.course_name}'")
                    return True

        return False

    def _is_valid_major_course(
        self,
        course: Courses,
        user_info: UserInfo,
        criteria: FilterCriteria
    ) -> bool:
        """전공 과목이 유효한지 확인"""
        # 학년 필터
        if course.target_year != "전학년":
            try:
                course_year = int(course.target_year[0])
            except Exception:
                course_year = 0
            if course_year > criteria.current_year:
                return False

        # 전공필수 학과 매칭
        if course.category.category_name == "전공필수":
            if not user_info.student_dept_id:
                # 학과 정보 없으면 포함 (테스트 모드)
                print(f"DEBUG: 전공필수 '{course.course_name}' 포함 - 학과 정보 없음 (테스트 모드)")
                return True

            # 관련 학과 확인
            is_related = self._is_related_department(
                course.dept_id,
                user_info.student_dept_id
            )

            if user_info.student_dept_id:
                if course.dept_id != user_info.student_dept_id and not is_related:
                    print(f"DEBUG: 전공필수 '{course.course_name}' 제외 - 관련없는 학과 과목 (과목 학과: {course.dept_id}, 학생 학과: {user_info.student_dept_id})")
                    return False
                else:
                    print(f"DEBUG: 전공필수 '{course.course_name}' 포함 - 같은/관련 학과 (과목 학과: {course.dept_id}, 학생 학과: {user_info.student_dept_id})")

        # 전공선택 학과 매칭
        elif course.category.category_name == "전공선택":
            if user_info.student_dept_id and course.dept_id:
                is_related = self._is_related_department(
                    course.dept_id,
                    user_info.student_dept_id
                )
                if course.dept_id != user_info.student_dept_id and not is_related:
                    print(f"DEBUG: 전공선택 '{course.course_name}' 제외 - 관련없는 학과 과목")
                    return False

        return True

    def _is_related_department(self, dept_id1: int, dept_id2: int) -> bool:
        """두 학과가 관련 학과인지 확인"""
        for group in RELATED_DEPT_GROUPS:
            if dept_id1 in group and dept_id2 in group:
                return True
        return False

    def _passes_basic_filters(
        self,
        course: Courses,
        criteria: FilterCriteria
    ) -> bool:
        """기본 필터 통과 확인

        Note:
            필수 과목(pre_added_ids)도 후보 목록에 포함되어야 합니다.
            이 과목들은 나중에 _build_candidate_data에서 pre_added=True로 표시되고,
            CP-SAT 모델에서 강제로 선택됩니다.
        """
        # 학점 0 이하
        if course.credits <= 0:
            return False

        # 시간표 '00' slot 제거
        if any(sch.times.strip() == EXCLUDE_TIME_SLOT for sch in course.courseschedule_set.all()):
            return False

        # 필수 과목(pre_added)은 공강일 필터를 무시
        if course.course_id in criteria.pre_added_ids:
            print(f"DEBUG: 필수 과목 '{course.course_name}' - 기본 필터 통과 (공강일 무시)")
            # 가상강의실 제외 (필수 과목도 체크)
            if any(EXCLUDE_LOCATION_KEYWORD in (sch.location or "") for sch in course.courseschedule_set.all()):
                return False
            return True

        # Free-day 충돌 (일반 과목만 체크)
        if any(sch.day in criteria.free_days for sch in course.courseschedule_set.all()):
            return False

        # 가상강의실 제외
        if any(EXCLUDE_LOCATION_KEYWORD in (sch.location or "") for sch in course.courseschedule_set.all()):
            return False

        return True

    def _is_valid_general_course(
        self,
        course: Courses,
        criteria: FilterCriteria
    ) -> bool:
        """교양 과목이 유효한지 확인"""
        # 교양은 전학년이어야 함
        if course.target_year != GENERAL_EDUCATION_TARGET_YEAR:
            return False

        # 시간대 선호도는 Hard Constraint에서 제거
        # → course_scorer.py에서 Soft Constraint(점수)로만 처리
        # 이유: 오전 선호 시 오전 과목 우선이지만, 오전이 부족하면 오후도 선택 가능해야 함

        # 교양 세부 항목 확인
        if criteria.missing_gen_sub:
            effective_cat = get_effective_general_category(course)
            shortage = criteria.missing_gen_sub.get(effective_cat, 0)

            # 이미 충족된 카테고리는 제외
            if shortage == 0:
                return False

            # 필요한 학점보다 큰 과목은 나중에 우선순위에서 조정
            if course.credits > shortage:
                print(f"DEBUG: '{course.course_name}' ({course.credits}학점) > {effective_cat} 필요({shortage}학점) - 우선순위 감소")

        return True

    def filter_by_same_year(
        self,
        candidate_data: List[Dict[str, Any]],
        user_info: UserInfo,
        target_major: int
    ) -> List[Dict[str, Any]]:
        """
        동일학년 전공선택 필터링

        Args:
            candidate_data: 후보 과목 데이터 리스트
            user_info: 사용자 정보
            target_major: 목표 전공 학점

        Returns:
            필터링된 후보 과목 데이터 리스트
        """
        current_year = user_info.current_year

        # 동일학년 전공선택 강좌 우선 필터링
        for data in candidate_data:
            if data['category'] == '전공선택':
                if data['year'] == "전학년" or (
                    data['year'] and data['year'][0].isdigit() and int(data['year'][0]) == current_year
                ):
                    data['is_same_year'] = True
                else:
                    data['is_same_year'] = False

        # 이미 추가된 전공 학점 계산
        pre_added_major = sum(
            data['credit'] for data in candidate_data
            if data['category'] in ['전공필수', '전공선택'] and data.get('pre_added', False)
        )

        # 동일학년 전공선택 우선순위 조정 (완전 제거 대신 가중치 조정)
        if pre_added_major < target_major:
            needed_major = target_major - pre_added_major
            available_same_year_elective = sum(
                data['credit'] for data in candidate_data
                if data['category'] == '전공선택' and data.get('is_same_year', False) and not data.get('pre_added', False)
            )

            # 동일학년 과목이 충분하면 하위학년 과목에 패널티 부여 (제거하지 않음)
            if available_same_year_elective >= needed_major * 1.5:  # 1.5배 이상 여유가 있을 때만
                for data in candidate_data:
                    if data['category'] == '전공선택' and data.get('is_same_year') is False:
                        # 졸업 우선순위를 낮춤 (제거하지 않고 우선순위 조정)
                        if 'graduation_priority' in data:
                            data['graduation_priority'] = max(0, data['graduation_priority'] - 30)
                        print(f"DEBUG: 하위학년 전공선택 {data['course_name']} 우선순위 감소")

            print(f"DEBUG: 동일학년 전공선택 {available_same_year_elective}학점, 필요 {needed_major}학점")

        return candidate_data

    def filter_by_exclude_courses(
        self,
        candidate_data: List[Dict[str, Any]],
        exclude_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        제외 과목 필터링 (candidate_data에서)

        Args:
            candidate_data: 후보 과목 데이터 리스트
            exclude_names: 제외할 과목명 리스트

        Returns:
            필터링된 후보 과목 데이터 리스트

        Note:
            필수 과목(pre_added=True)은 제외 목록에 있어도 필터링하지 않습니다.
        """
        if not exclude_names:
            return candidate_data

        print("DEBUG: Applying exclude_courses filter:", exclude_names)
        filtered = []

        for d in candidate_data:
            # 필수 과목은 항상 포함
            if d.get('pre_added', False):
                filtered.append(d)
                print(f"DEBUG: 필수 과목 제외 필터 무시 - {d['course_name']}")
                continue

            course_name = d['course_name'].strip()
            should_exclude = False

            for exclude_name in exclude_names:
                exclude_name = exclude_name.strip()
                if not exclude_name:
                    continue

                # 정확한 매칭
                if course_name.lower() == exclude_name.lower():
                    should_exclude = True
                    print(f"DEBUG: Exact match exclusion: '{course_name}' == '{exclude_name}'")
                    break

                # 부분 매칭
                if exclude_name.lower() in course_name.lower():
                    should_exclude = True
                    print(f"DEBUG: Partial match exclusion: '{exclude_name}' in '{course_name}'")
                    break

                # 역방향 부분 매칭
                if course_name.lower() in exclude_name.lower():
                    should_exclude = True
                    print(f"DEBUG: Reverse partial match exclusion: '{course_name}' in '{exclude_name}'")
                    break

            if not should_exclude:
                filtered.append(d)
            else:
                print(f"DEBUG: Excluded course: {course_name}")

        print("DEBUG: after exclude_courses filter:", len(filtered))
        return filtered
