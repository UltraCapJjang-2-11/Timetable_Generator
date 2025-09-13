# data_manager/course/course_filter_service.py

from django.db.models import Q
from data_manager.models import (
    Courses, Department, Category, CourseSchedule, Semester, College
)

class CourseFilterService:

    """
    Course에 대한 다양한 검색 기능을 제공하는 서비스 클래스
    - 단일 조건 필터 메서드(학과, 카테고리, 교수명, 시간제외, 학점, 강의명)와
    - 종합적으로 필터링하여 결과를 반환하는 get_final_results를 함께 제공
    """

    def get_all_courses(self):
        """
        기본적으로 전체 Course를 반환
        """
        return Courses.objects.all()

    # -----------------------------
    # (1) 학과 필터
    # -----------------------------
    def filter_by_department(self, queryset, dept_name):
        """
        dept_name(예: '소프트웨어학부')로 DEPARTMENT 테이블에서 dept_id를 구하고,
        해당 dept_id를 가진 Course들만 필터링
        """
        try:
            department = Department.objects.get(dept_name=dept_name)
            return queryset.filter(dept_id=department.dept_id)
        except Department.DoesNotExist:
            # 학과명이 존재하지 않으면 결과가 없으므로 빈 QuerySet 반환
            return queryset.none()

    # -----------------------------
    # (2) 단과대학 필터
    # -----------------------------
    def filter_by_college(self, queryset, college_name: str) :
        """
        college_name(예: '전자정보대학')로 해당 단과대학에 속한 학과들의 dept_id를 구하고,
        그 dept_id들중 하나라도 속하지 않은 Course를 제외한 나머지 Course만 반환합니다.
        """
        try:
            # 1) 단과대학 객체 찾기
            college = College.objects.get(college_name=college_name)

            # 2) 해당 단과대학에 속한 모든 학과 ID 리스트 추출
            dept_ids = Department.objects.filter(
                college_id=college.college_id
            ).values_list('dept_id', flat=True)

            # 3) Course 중에서 위 dept_ids에 속하는 것만 남기기
            return queryset.filter(dept_id__in=list(dept_ids))

        except College.DoesNotExist:
            # 단과대학이 없으면 빈 QuerySet 반환
            return queryset.none()

    # -----------------------------
    # (2) 카테고리 필터
    # -----------------------------

    def filter_by_category(self, queryset, category_name):
        """
        category_name(예: '확대교양')에 해당하는 Category 및
        모든 하위 Category의 ID를 찾아서 필터링
        """
        # 1) 루트 카테고리 가져오기 - 여러 개가 있을 수 있으므로 filter 사용
        root_categories = Category.objects.filter(category_name=category_name)

        if not root_categories.exists():
            return queryset.none()

        # 여러 카테고리가 있으면 가장 최신 version_year를 가진 것을 선택
        root_category = root_categories.order_by('-version_year').first()

        # 2) 해당 카테고리의 모든 하위 카테고리 ID를 재귀적으로 구하기
        category_ids = self._get_all_subcategory_ids(root_category)
        # 루트 카테고리 자기 자신도 포함
        category_ids.append(root_category.category_id)

        # 3) 해당 ID들을 가진 Course들만 필터링
        return queryset.filter(category_id__in=category_ids)

    def filter_by_category_id(self, queryset, category_id):
        """
        category_name(예: '확대교양')에 해당하는 Category 및
        모든 하위 Category의 ID를 찾아서 필터링
        """
        # 1) 루트 카테고리 가져오기
        try:
            root_category = Category.objects.get(category_id=category_id)
        except Category.DoesNotExist:
            return queryset.none()

        # 2) 해당 카테고리의 모든 하위 카테고리 ID를 재귀적으로 구하기
        category_ids = self._get_all_subcategory_ids(root_category)
        # 루트 카테고리 자기 자신도 포함
        category_ids.append(root_category.category_id)

        # 3) 해당 ID들을 가진 Course들만 필터링
        return queryset.filter(category_id__in=category_ids)

    def _get_all_subcategory_ids(self, parent_category):
        """
        재귀적으로 parent_category의 자식, 손자 ... 모든 category_id를 수집
        """
        result = []
        children = Category.objects.filter(parent_category_id=parent_category.category_id)
        for child in children:
            result.append(child.category_id)
            result.extend(self._get_all_subcategory_ids(child))
        return result

    # -----------------------------
    # (3) 교수명 필터
    # -----------------------------
    def filter_by_instructor(self, queryset, instructor_name):
        """
        instructor(교수명)를 부분 일치로 필터링
        """
        return queryset.filter(instructor_name__icontains=instructor_name)

    # -----------------------------
    # (4) 특정 시간대 제외
    # -----------------------------
    def filter_by_exclude_times(self, queryset, exclude_day_time_map):
        """
        exclude_day_time_map 예시:
            {
                '월': ['03','04'],
                '화': ['02']
            }
        위 요일+교시를 포함한 강의들은 제외

        1) CourseSchedule에서 해당 요일+교시를 가진 course_id들을 구한 뒤
        2) 이 course_id들을 exclude() 처리
        """
        if not exclude_day_time_map:
            return queryset

        # Q 객체로 제외 조건을 생성
        q_exclude = Q()
        for day, times_list in exclude_day_time_map.items():
            for t in times_list:
                # day='월' AND times__contains='03' ... 등을 OR로 결합
                q_exclude |= Q(day=day, times__contains=t)

        # 제외 대상 강의 ID
        course_ids = CourseSchedule.objects.filter(q_exclude).values_list('course_id', flat=True)
        return queryset.exclude(course_id__in=course_ids)

    # -----------------------------
    # (5) 학점 필터
    # -----------------------------
    def filter_by_credit(self, queryset, credit):

        """
        예: credit=3 -> 3학점인 강의만 필터
        """
        return queryset.filter(credits=credit)

    # -----------------------------
    # (6) 강의명 필터
    # -----------------------------
    def filter_by_course_name(self, queryset, course_name):
        """
        course_name 부분 일치 검색
        """
        return queryset.filter(course_name__icontains=course_name)

    # -----------------------------
    # (7) 학기 필터: 학년도와 학기를 이용하여 필터링
    # -----------------------------

    def _get_semester_id_from_year_term(self, year, term):
        """
        학년도(year)와 학기(term)를 입력받아 해당 Semester 객체의 ID를 반환.
        변환 실패 시 None 반환.
        """
        try:
            year_int = int(year)
        except (ValueError, TypeError):
            return None

        try:
            semester_obj = Semester.objects.get(year=year_int, term=term)
            return semester_obj.semester_id
        except Semester.DoesNotExist:
            return None

    def filter_by_semester_terms(self, queryset, year, term):
        """
        year와 term을 사용해 학기 ID를 조회하고, 해당 학기에 개설된 강의만 필터링.
        학기 정보가 없으면 빈 QuerySet 반환.
        """
        sem_id = self._get_semester_id_from_year_term(year, term)
        if sem_id is not None:
            return queryset.filter(semester_id=sem_id)
        else:
            return queryset.none()

    # -----------------------------
    # (8) 종합 검색
    # -----------------------------
    def course_search(
        self,
        college_name=None,

        dept_name=None,
        category_name=None,
        category_id=None,
        instructor_name=None,
        exclude_day_time_map=None,
        credit=None,
        course_name=None,
        year=2025,
        term='2학기'
    ):
        """
        여러 조건을 동시에 받아서 필터링 체이닝.
        학년도(year)와 학기(term)가 주어지면, 해당 학기의 강의만 반환.
        """
        queryset = self.get_all_courses()

        if college_name:
            queryset = self.filter_by_college(queryset, college_name)
        if dept_name:
            queryset = self.filter_by_department(queryset, dept_name)
        if category_name:
            queryset = self.filter_by_category(queryset, category_name)
        if category_id:
            queryset = self.filter_by_category_id(queryset, category_id)
        if instructor_name:
            queryset = self.filter_by_instructor(queryset, instructor_name)
        if exclude_day_time_map:
            queryset = self.filter_by_exclude_times(queryset, exclude_day_time_map)
        if credit is not None:
            queryset = self.filter_by_credit(queryset, credit)
        if course_name:
            queryset = self.filter_by_course_name(queryset, course_name)
        if year and term:
            queryset = self.filter_by_semester_terms(queryset, year, term)

        return queryset
