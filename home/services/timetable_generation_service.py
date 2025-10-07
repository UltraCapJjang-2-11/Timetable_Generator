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
        model, x, objective_expr = self.model_builder.build_model(candidate_data, constraints)

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

        # 13. Phase 2: 다양한 해 찾기 (Phase 1의 최적값 활용)
        timetables_data = self.solution_finder.find_multiple_solutions(
            model,
            x,
            candidate_data,
            score_criteria.review_summaries,
            optimal_value=best_value,  # Phase 1 최적값 전달
            objective_expr=objective_expr  # 목적함수 표현식 전달
        )

        # 14. 선호도 기반 정렬
        sorted_timetables = self._sort_by_preference(
            timetables_data,
            request_params
        )

        # 전체 프로세스 요약
        print("\n" + "="*80)
        print("📊 시간표 생성 프로세스 최종 요약")
        print("="*80)
        print(f"✅ 후보 과목 수: {len(candidates)}개")
        print(f"✅ 시간 제약 적용 후: {len(candidate_data)}개")
        print(f"✅ Phase 1 최적해: {best_value:,.0f}점")
        print(f"✅ Phase 2 생성 시간표: {len(timetables_data)}개")
        print(f"✅ 최종 선별 시간표: {len(sorted_timetables)}개")

        if sorted_timetables:
            print("\n📋 사용자 요구사항 충족도:")
            print(f"  - 목표 총 학점: {request_params.target_total}")
            print(f"  - 목표 전공 학점: {request_params.target_major}")
            print(f"  - 목표 교양 학점: {request_params.target_elective}")

            # 첫 번째 시간표 기준 충족도 확인
            first_timetable = sorted_timetables[0]
            total_credits = sum(course['credits'] for course in first_timetable)
            major_credits = sum(course['credits'] for course in first_timetable
                              if course['category_name'] in ['전공필수', '전공선택'])
            elective_credits = sum(course['credits'] for course in first_timetable
                                 if course['category_name'] not in ['전공필수', '전공선택'])

            print(f"\n  최상위 시간표 학점 분석:")
            print(f"    - 실제 총 학점: {total_credits} (목표: {request_params.target_total})")
            print(f"    - 실제 전공 학점: {major_credits} (목표: {request_params.target_major})")
            print(f"    - 실제 교양 학점: {elective_credits} (목표: {request_params.target_elective})")

        print("\n✅ 시간표 생성 완료!")
        print("="*80 + "\n")

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
        timetables: List[Dict[str, Any]],  # 구조 변경: Dict로 수정
        request_params: TimetableRequest
    ) -> List[List[Dict[str, Any]]]:
        """선호도 기반 시간표 정렬"""
        print("\n" + "="*80)
        print("📊 선호도 기반 시간표 정렬 및 선별")
        print("="*80)

        # ScoreCriteria 생성 (간소화 버전) - prefer_compact 추가
        score_criteria = ScoreCriteria(
            preferred_instructors=request_params.preferred_instructors,
            avoid_instructors=request_params.avoid_instructors,
            preferred_courses=request_params.preferred_courses,
            avoid_courses=request_params.avoid_courses,
            prefer_morning=request_params.prefer_morning,
            prefer_afternoon=request_params.prefer_afternoon,
            prefer_compact=request_params.prefer_compact  # 밀집도 선호 추가
        )

        # 선호 조건 출력
        print("📌 사용자 선호 조건:")
        if request_params.preferred_instructors:
            print(f"  - 선호 교수: {', '.join(request_params.preferred_instructors)}")
        if request_params.avoid_instructors:
            print(f"  - 기피 교수: {', '.join(request_params.avoid_instructors)}")
        if request_params.preferred_courses:
            print(f"  - 선호 과목: {', '.join(request_params.preferred_courses)}")
        if request_params.avoid_courses:
            print(f"  - 기피 과목: {', '.join(request_params.avoid_courses)}")
        if request_params.prefer_morning:
            print("  - 오전 시간대 선호")
        if request_params.prefer_afternoon:
            print("  - 오후 시간대 선호")

        print(f"\n총 {len(timetables)}개 시간표 평가 시작...")
        print("-" * 80)

        # 각 시간표에 선호도 점수 계산 및 추가
        scored_timetables = []
        for idx, timetable_data in enumerate(timetables):
            # 시간표 과목 리스트 추출
            timetable = timetable_data['courses']
            objective_value = timetable_data.get('objective_value', 0)
            objective_percentage = timetable_data.get('objective_percentage', 0)

            score, matched = self.scorer.calculate_timetable_preference_score(
                timetable,
                score_criteria
            )
            recommendation_level = self.scorer.get_recommendation_level(score)

            # 종합 점수 계산: 목적함수 값 + 선호도 보너스
            # 목적함수 값을 1/1000로 스케일링하여 선호도 점수와 균형 맞춤
            combined_score = (objective_value / 1000) + score

            scored_timetables.append({
                'number': idx + 1,
                'preference_score': score,
                'objective_value': objective_value,
                'objective_percentage': objective_percentage,
                'combined_score': combined_score,
                'timetable': timetable,
                'matched': matched,
                'recommendation': recommendation_level,
                'num_courses': len(timetable)
            })

        # 종합 점수로 정렬 (높은 점수가 먼저)
        # 1차: combined_score, 2차: objective_value
        scored_timetables.sort(key=lambda x: (x['combined_score'], x['objective_value']), reverse=True)

        # 점수 분포 분석
        pref_scores = [st['preference_score'] for st in scored_timetables]
        obj_values = [st['objective_value'] for st in scored_timetables]
        combined_scores = [st['combined_score'] for st in scored_timetables]

        print("\n📈 점수 분포 분석:")
        print("1️⃣ 목적함수 값:")
        print(f"  - 최고: {max(obj_values):,.0f} ({max(st['objective_percentage'] for st in scored_timetables):.1f}%)")
        print(f"  - 최저: {min(obj_values):,.0f} ({min(st['objective_percentage'] for st in scored_timetables):.1f}%)")
        print(f"  - 평균: {sum(obj_values)/len(obj_values):,.0f}")

        print("\n2️⃣ 선호도 점수:")
        print(f"  - 최고: {max(pref_scores)}점")
        print(f"  - 최저: {min(pref_scores)}점")
        print(f"  - 평균: {sum(pref_scores)/len(pref_scores):.1f}점")

        print("\n3️⃣ 종합 점수 (목적함수/1000 + 선호도):")
        print(f"  - 최고: {max(combined_scores):.1f}점")
        print(f"  - 최저: {min(combined_scores):.1f}점")
        print(f"  - 평균: {sum(combined_scores)/len(combined_scores):.1f}점")

        # 상위 20개와 나머지 비교
        top_20 = scored_timetables[:20]
        rest = scored_timetables[20:] if len(scored_timetables) > 20 else []

        if top_20:
            top_20_avg = sum(st['combined_score'] for st in top_20) / len(top_20)
            print(f"\n📊 상위 20개 시간표:")
            print(f"  - 평균 종합점수: {top_20_avg:.1f}점")
            print(f"  - 종합점수 범위: {top_20[-1]['combined_score']:.1f}점 ~ {top_20[0]['combined_score']:.1f}점")
            print(f"  - 목적함수 범위: {min(st['objective_value'] for st in top_20):,.0f} ~ {max(st['objective_value'] for st in top_20):,.0f}")

            # 상위 5개 시간표 상세 정보
            print("\n🏆 상위 5개 시간표 상세:")
            print("-" * 120)
            print(f"{'순위':4} {'목적함수':>10} {'선호도':>8} {'종합점수':>10} {'추천':5} {'과목수':>6} {'주요 과목'}")
            print("-" * 120)

            for i, st in enumerate(top_20[:5]):
                course_names = [c['course_name'] for c in st['timetable']]
                main_courses = ', '.join(course_names[:3]) + ('...' if len(course_names) > 3 else '')
                print(f"{i+1:4d} {st['objective_value']:10,.0f} {st['preference_score']:8d} "
                      f"{st['combined_score']:10.1f} {st['recommendation']:5} {st['num_courses']:6d} "
                      f"{main_courses}")

        if rest:
            rest_avg = sum(st['combined_score'] for st in rest) / len(rest)
            print(f"\n📊 나머지 {len(rest)}개 시간표:")
            print(f"  - 평균 종합점수: {rest_avg:.1f}점")
            print(f"  - 종합점수 범위: {rest[-1]['combined_score']:.1f}점 ~ {rest[0]['combined_score']:.1f}점")
            print(f"  - 상위 20개 대비 평균 종합점수 차이: {top_20_avg - rest_avg:.1f}점")
            print(f"  - 목적함수 범위: {min(st['objective_value'] for st in rest):,.0f} ~ {max(st['objective_value'] for st in rest):,.0f}")

        # 정렬된 시간표 리스트 생성
        sorted_timetables = [st['timetable'] for st in scored_timetables]

        # 상위 20개만 반환
        top_timetables = sorted_timetables[:20]

        print(f"\n✅ 최종 선별: 총 {len(sorted_timetables)}개 중 상위 {len(top_timetables)}개 시간표 제공")
        print("="*80 + "\n")

        return top_timetables
