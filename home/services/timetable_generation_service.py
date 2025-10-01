"""
시간표 생성 메인 서비스
모든 하위 서비스를 조율하여 시간표 생성 프로세스 관리
"""

import re
from typing import List, Dict, Any, Optional
from django.contrib.auth.models import User
from django.db.models.functions import Upper

from data_manager.models import (
    Courses, UserProfile, UserGraduationProgress,
    Transcript, CourseReviewSummary
)
from data_manager.services.course_filter_service import CourseFilterService

from ..views.timetable_types import (
    TimetableRequest, UserInfo, FilterCriteria, ScoreCriteria,
    ConstraintData
)
from ..views.timetable_config import (
    CURRENT_YEAR, CURRENT_TERM,
    ValidationMessages, CLASS_START_HOUR
)
from ..utils import (
    get_effective_general_category, get_simplified_category_name,
    apply_time_constraints
)

from .parameter_parser import ParameterParser
from .candidate_filter import CandidateFilter
from .course_scorer import CourseScorer
from .timetable_optimizer import ModelBuilder, SolutionFinder
from .building_distance_service import extract_building_number


class TimetableGenerationService:
    """시간표 생성 메인 서비스"""

    def __init__(self):
        self.parser = ParameterParser()
        self.candidate_filter = CandidateFilter()
        self.scorer = CourseScorer()
        self.model_builder = ModelBuilder()
        self.solution_finder = SolutionFinder()
        self.course_service = CourseFilterService()

    def generate(
        self,
        user: User,
        request_params: TimetableRequest
    ) -> Dict[str, Any]:
        """
        시간표 생성 메인 함수

        Args:
            user: Django User 객체
            request_params: 시간표 생성 요청 파라미터

        Returns:
            생성된 시간표 결과 딕셔너리
        """
        print("DEBUG: --- Timetable Generation Start ---")

        # 1. 필수 과목 ID 파싱
        req_ids = self._parse_required_courses(request_params.required_courses)
        request_params.existing_courses = list(set(request_params.existing_courses + req_ids))
        print("DEBUG: final pre_added_ids (기존+필수과목) =", request_params.existing_courses)

        # 2. 사용자 정보 로드
        user_info = self._load_user_info(user)
        print("DEBUG: student_dept_id =", user_info.student_dept_id)
        print("DEBUG: current_year =", user_info.current_year)

        # 3. 필터링 기준 생성
        filter_criteria = self._create_filter_criteria(user_info, request_params)

        # 4. 후보 과목 조회 및 필터링
        candidates = self.candidate_filter.get_candidates(user_info, filter_criteria)
        print("DEBUG: candidates count =", len(candidates))

        # 5. 점수 계산 기준 생성
        score_criteria = self._create_score_criteria(user_info, request_params)

        # 6. 후보 과목 점수 계산
        self.scorer.calculate_scores(candidates, score_criteria)

        # 7. 후보 과목 데이터 구성
        candidate_data = self._build_candidate_data(
            candidates,
            request_params.existing_courses
        )
        print("DEBUG: candidate_data count (before filter) =", len(candidate_data))

        # 8. 시간 제약 조건 적용
        candidate_data = apply_time_constraints(
            candidate_data,
            request_params.only_time_ranges,
            request_params.avoid_times,
            request_params.avoid_time_ranges,
            request_params.specific_avoid_times,
            request_params.specific_avoid_time_ranges
        )
        print("DEBUG: candidate_data count (after time constraints) =", len(candidate_data))

        # 9. 동일학년 전공선택 필터링
        candidate_data = self.candidate_filter.filter_by_same_year(
            candidate_data,
            user_info,
            request_params.target_major
        )

        # 10. 제외 과목 필터링
        candidate_data = self.candidate_filter.filter_by_exclude_courses(
            candidate_data,
            request_params.exclude_courses
        )
        print("DEBUG: candidate_data count (final) =", len(candidate_data))

        # 11. CP-SAT 모델 구성
        constraints = ConstraintData(
            target_total=request_params.target_total,
            target_major=request_params.target_major,
            target_elective=request_params.target_elective,
            missing_gen_sub=user_info.missing_gen_sub,
            max_walking_time=request_params.max_walking_time,
            prefer_compact=request_params.prefer_compact
        )
        model, x = self.model_builder.build_model(candidate_data, constraints)

        # 12. Phase 1: 최적해 찾기
        best_value = self.solution_finder.find_optimal_solution(
            model,
            x,
            candidate_data
        )
        if best_value is None:
            return {
                'progress': '완료',
                'found': 0,
                'timetables': [],
                'message': ValidationMessages.NO_SOLUTION_FOUND
            }

        # 13. Phase 2: 다양한 해 찾기
        timetables_data = self.solution_finder.find_multiple_solutions(
            model,
            x,
            candidate_data,
            score_criteria.review_summaries
        )

        # 14. 선호도 기반 정렬
        sorted_timetables = self._sort_by_preference(
            timetables_data,
            request_params
        )

        print("DEBUG: Total unique solutions found:", len(sorted_timetables))
        print("DEBUG: --- Timetable Generation End ---")

        # 15. 결과 반환
        return {
            'progress': '완료',
            'found': len(sorted_timetables),
            'timetables': sorted_timetables,
            'message': ValidationMessages.SUCCESS_MESSAGE_TEMPLATE.format(count=len(sorted_timetables)) if sorted_timetables else ValidationMessages.NO_TIMETABLE_FOUND
        }

    def _parse_required_courses(self, req_names: List[str]) -> List[int]:
        """필수 과목명을 Course ID 리스트로 변환"""
        req_ids = []
        major_qs = (
            self.course_service.course_search(year=CURRENT_YEAR, term=CURRENT_TERM, category_name='교양') |
            self.course_service.course_search(year=CURRENT_YEAR, term=CURRENT_TERM, category_name='전공')
        )
        for name in req_names:
            course = major_qs.filter(course_name__icontains=name).first()
            if course:
                req_ids.append(course.course_id)
        print("DEBUG: parsed required course IDs =", req_ids)
        return req_ids

    def _load_user_info(self, user: User) -> UserInfo:
        """사용자 정보 로드"""
        student_id = user.id if user.is_authenticated else 1
        user_profile = None
        graduation_progress = []
        completed_courses = set()
        missing_gen_sub = {}

        if user.is_authenticated:
            user_profile = UserProfile.objects.filter(user=user).first()
            if user_profile:
                # 졸업 진행 상황 로드
                graduation_progress = list(UserGraduationProgress.objects.filter(
                    user_profile=user_profile,
                    is_satisfied=False,
                    shortage_credits__gt=0
                ).select_related('category').order_by('-shortage_credits'))

                # 이수한 과목 목록 로드
                transcripts = Transcript.objects.filter(
                    user_profile=user_profile
                ).select_related('course')
                completed_courses = {t.course.course_name.strip().upper() for t in transcripts}

                # 교양 세부 이수 상태 처리
                for progress in graduation_progress:
                    if progress.shortage_credits > 0:
                        cat_name = progress.category.category_name
                        missing_gen_sub[cat_name] = int(progress.shortage_credits)

        # 학년 정보
        try:
            if user_profile and user_profile.current_grade:
                current_year = user_profile.current_grade
                if current_year >= 4:
                    current_year = 100
            else:
                current_year = 3
        except Exception:
            current_year = 3

        # 학과 정보
        student_dept_id = None
        dept_name = ""
        if user_profile and user_profile.department:
            student_dept_id = user_profile.department.dept_id
            dept_name = user_profile.department.dept_name
            print(f"DEBUG: UserProfile에서 학과 정보 사용 - {dept_name} (ID: {student_dept_id})")
        else:
            print("DEBUG: 학과 정보 없음 - 학과 필터링 비활성화")

        return UserInfo(
            user_id=student_id,
            student_dept_id=student_dept_id,
            dept_name=dept_name,
            current_year=current_year,
            completed_courses=completed_courses,
            missing_gen_sub=missing_gen_sub,
            graduation_progress=graduation_progress
        )

    def _create_filter_criteria(
        self,
        user_info: UserInfo,
        request_params: TimetableRequest
    ) -> FilterCriteria:
        """필터링 기준 생성"""
        return FilterCriteria(
            student_dept_id=user_info.student_dept_id,
            current_year=user_info.current_year,
            completed_courses=user_info.completed_courses,
            exclude_names=request_params.exclude_courses,
            free_days=request_params.free_days,
            pre_added_ids=request_params.existing_courses,
            missing_gen_sub=user_info.missing_gen_sub
        )

    def _create_score_criteria(
        self,
        user_info: UserInfo,
        request_params: TimetableRequest
    ) -> ScoreCriteria:
        """점수 계산 기준 생성"""
        # 졸업요건 우선순위 맵 생성
        priority_map = {}
        if user_info.graduation_progress:
            for progress in user_info.graduation_progress:
                category_id = progress.category_id
                shortage = float(progress.shortage_credits)
                priority_map[category_id] = min(shortage * 10, 100)
                print(f"DEBUG: 졸업요건 우선순위 - {progress.category.category_name}: {shortage}학점 부족 (우선순위: {priority_map[category_id]}점)")

        # 평점 정보 로드
        review_summaries = {}
        for summary in CourseReviewSummary.objects.filter(avg_rating__isnull=False):
            key = (summary.course_name, summary.instructor_name)
            review_summaries[key] = summary
        print(f"DEBUG: Loaded {len(review_summaries)} course review summaries")

        return ScoreCriteria(
            priority_map=priority_map,
            preferred_instructors=request_params.preferred_instructors,
            avoid_instructors=request_params.avoid_instructors,
            preferred_courses=request_params.preferred_courses,
            avoid_courses=request_params.avoid_courses,
            preference_tags=request_params.preference_tags,
            prefer_morning=request_params.prefer_morning,
            prefer_afternoon=request_params.prefer_afternoon,
            missing_gen_sub=user_info.missing_gen_sub,
            review_summaries=review_summaries
        )

    def _build_candidate_data(
        self,
        courses: List[Courses],
        pre_added_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """후보 과목 데이터 구성"""
        candidate_data = []

        for course in courses:
            schedule_list = []
            locations = []

            for sch in course.courseschedule_set.all():
                raw = sch.times.strip()
                if "@" in raw:
                    parts = raw.split("@", 1)
                    raw_time = parts[0].strip()
                    loc = parts[1].strip()
                else:
                    raw_time = raw
                    loc = sch.location
                if not raw_time:
                    continue

                schedule_list.append({
                    'day': sch.day,
                    'times': raw_time,
                    'location': loc
                })
                locations.append(loc)

            if not schedule_list:
                continue

            data_item = {
                'id': course.course_id,
                'course_name': course.course_name,
                'course_code': course.course_code,
                'section': course.section,
                'credit': course.credits,
                'credits': course.credits,
                'year': course.target_year,
                'instructor_name': course.instructor_name,
                'capacity': course.capacity,
                'dept_name': course.dept.dept_name if course.dept else '',
                'category': get_simplified_category_name(course),
                'semester': f"{CURRENT_YEAR} {CURRENT_TERM}",
                'schedule': schedule_list,
                'location': locations[0] if locations else "",
                'pre_added': course.course_id in pre_added_ids,
                'graduation_priority': getattr(course, 'graduation_priority', 0),
                'preference_score': getattr(course, 'preference_score', 0),
                'rating_score': getattr(course, 'rating_score', 0)
            }

            # 교양 강좌: effective_category 추가
            if get_effective_general_category(course):
                data_item['effective_category'] = get_effective_general_category(course)

            # 건물 번호 추출
            building_numbers = []
            for loc in locations:
                building = extract_building_number(loc)
                if building:
                    building_numbers.append(building)
            data_item['buildings'] = building_numbers

            candidate_data.append(data_item)

        return candidate_data

    def _sort_by_preference(
        self,
        timetables: List[List[Dict[str, Any]]],
        request_params: TimetableRequest
    ) -> List[List[Dict[str, Any]]]:
        """선호도 기반 시간표 정렬"""
        print("DEBUG: Starting preference-based sorting and filtering...")

        # ScoreCriteria 생성 (간소화 버전)
        score_criteria = ScoreCriteria(
            preferred_instructors=request_params.preferred_instructors,
            avoid_instructors=request_params.avoid_instructors,
            preferred_courses=request_params.preferred_courses,
            avoid_courses=request_params.avoid_courses,
            prefer_morning=request_params.prefer_morning,
            prefer_afternoon=request_params.prefer_afternoon
        )

        # 각 시간표에 선호도 점수 계산 및 추가
        scored_timetables = []
        for idx, timetable in enumerate(timetables):
            print(f"\nDEBUG: 시간표 #{idx+1} 선호도 평가:")
            score, matched = self.scorer.calculate_timetable_preference_score(
                timetable,
                score_criteria
            )
            recommendation_level = self.scorer.get_recommendation_level(score)

            scored_timetables.append((score, timetable))
            print(f"  총 선호도 점수: {score}점, 추천 레벨: {recommendation_level}")

        # 선호도 점수로 정렬 (높은 점수가 먼저)
        scored_timetables.sort(key=lambda x: x[0], reverse=True)

        # 정렬된 시간표 리스트 생성
        sorted_timetables = [t[1] for t in scored_timetables]

        # 최고/최저 점수 출력
        if scored_timetables:
            best_score = scored_timetables[0][0]
            worst_score = scored_timetables[-1][0]
            print(f"\nDEBUG: 선호도 점수 범위: {worst_score}점 ~ {best_score}점")
            print(f"DEBUG: 최고 점수 시간표가 첫 번째로 배치됨 (점수: {best_score})")

        return sorted_timetables
