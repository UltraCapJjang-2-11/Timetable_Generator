"""
시간표 생성 및 관리 관련 뷰
시간표 생성 알고리즘, 저장, 삭제 등의 시간표 관리 기능을 담당.
"""

import os
import json
import traceback
from collections import defaultdict
from django.db.models.functions import Upper
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from ortools.sat.python import cp_model

from data_manager.services.course_filter_service import CourseFilterService
from data_manager.models import *
from ..utils import (
    get_effective_general_category, get_simplified_category_name,
    extract_missing_required_major_courses, apply_time_constraints, DummyObj
)
import re


def timetable_view(request):
    """
    시간표 생성 메인 페이지
    각 카테고리별 강의 목록을 조회하여 프론트엔드에 전달
    """
    service = CourseFilterService()

    # 25년도 1학기
    year = 2025
    term = "1학기"

    # 각 카테고리별 강의 조회
    major_required = service.course_search(year=year, term=term, category_name='전공필수').order_by('course_name')
    major_elective = service.course_search(year=year, term=term, category_name='전공선택').order_by('course_name')
    general_elective = service.course_search(year=year, term=term, category_name='교양').order_by('course_name')
    free_elective = service.course_search(year=year, term=term, category_name='일선').order_by('course_name')
    teaching_required = service.course_search(year=year, term=term, category_name='교직').order_by('course_name')

    return render(request, "home/timetable/timetable.html", {
        'major_required': major_required,
        'major_elective': major_elective,
        'general_elective': general_elective,
        'free_elective': free_elective,
        'teaching_required': teaching_required,
    })


def extract_building_number(location):
    """
    강의실 위치에서 건물 번호 추출
    예: "N14-1325" -> "N14", "S1-4217" -> "S1"
    """
    if not location:
        return None
    # 정규 표현식으로 건물 번호 추출
    match = re.match(r'^([NSEW]\d+)', location.upper())
    if match:
        return match.group(1)
    return None


# 건물 거리 캐시 (전역 변수로 한 번만 로드)
_distance_cache = None

def load_distance_cache():
    """건물 거리 데이터를 메모리에 캐싱"""
    global _distance_cache
    if _distance_cache is None:
        _distance_cache = {}
        for dist in BuildingDistance.objects.all():
            key = (dist.from_building, dist.to_building)
            _distance_cache[key] = dist.walking_time
        print(f"DEBUG: 건물 거리 캐시 로드 완료 - {len(_distance_cache)}개 항목")
    return _distance_cache

def get_building_distance(from_building, to_building):
    """
    두 건물 간 이동 시간 조회 (캐시 사용)
    """
    if not from_building or not to_building:
        return 0
    if from_building == to_building:
        return 0

    # 캐시 확인
    cache = load_distance_cache()
    return cache.get((from_building, to_building), 5)


def generate_timetable_stream(request):
    """
    시간표 생성 메인 함수
    사용자 제약조건을 기반으로 최적의 시간표 조합을 생성
    CP-SAT 알고리즘을 사용하여 최적화 문제를 해결
    """
    year = 2025
    term = '1학기'

    try:
        print("DEBUG: --- Timetable Generation Start ---")

        # 0) 자연어 파싱으로 받아온 필수 과목명 → Course ID 리스트(req_ids)
        req_names = request.GET.getlist('required_courses[]')
        req_ids = []
        
        svc = CourseFilterService()
        # 미리 연도·학기·카테고리를 넣어서 기본 queryset을 받아옵니다.
        # 전공과 교양의 모든 하위 카테고리를 포함하도록 수정
        major_qs = (
            svc.course_search(year=year, term=term, category_name='교양') |
            svc.course_search(year=year, term=term, category_name='전공')
        )
        for name in req_names:
            course = major_qs.filter(course_name__icontains=name).first()
            if course:
                req_ids.append(course.course_id)
        print("DEBUG: parsed required course IDs =", req_ids)

        # 1) GET 파라미터 파싱 (공강, 기존 추가 과목, 학점 등)
        free_days = request.GET.getlist('free_days[]')
        existing_ids = request.GET.getlist('existing_courses[]')
        exclude_names = request.GET.getlist('exclude_courses[]')
        print("DEBUG: exclude_courses =", exclude_names)

        # 선호도 파라미터 파싱
        preferred_instructors = request.GET.getlist('preferred_instructors[]')
        avoid_instructors = request.GET.getlist('avoid_instructors[]')
        preferred_courses = request.GET.getlist('preferred_courses[]')
        avoid_courses = request.GET.getlist('avoid_courses[]')
        max_walking_time = int(request.GET.get('max_walking_time', 10))
        prefer_compact = request.GET.get('prefer_compact', 'false').lower() == 'true'
        prefer_morning = request.GET.get('prefer_morning', 'false').lower() == 'true'
        prefer_afternoon = request.GET.get('prefer_afternoon', 'false').lower() == 'true'

        # 교양 과목 태그 파라미터 파싱
        preference_tags = request.GET.getlist('preference_tags[]')
        print("DEBUG: preference_tags =", preference_tags)

        print("DEBUG: preferred_instructors =", preferred_instructors)
        print("DEBUG: avoid_instructors =", avoid_instructors)
        print("DEBUG: max_walking_time =", max_walking_time)
        
        try:
            pre_added_ids = [int(cid) for cid in existing_ids]
        except ValueError:
            pre_added_ids = []

        pre_added_ids = list(set(pre_added_ids + req_ids))
        print("DEBUG: final pre_added_ids (기존+필수과목) =", pre_added_ids)

        # 목표 학점 설정 및 검증
        try:
            target_total = int(request.GET.get('total_credits', 18))
            target_major = int(request.GET.get('major_credits', 9))
            target_elective = int(request.GET.get('elective_credits', 9))

            # CourseReviewSummary 데이터 미리 로드 (평점 기반 가중치용)
            review_summaries = {}
            for summary in CourseReviewSummary.objects.filter(avg_rating__isnull=False):
                # course_name과 instructor_name을 키로 사용 (과목코드가 달라도 매칭 가능)
                key = (summary.course_name, summary.instructor_name)
                review_summaries[key] = summary
            print(f"DEBUG: Loaded {len(review_summaries)} course review summaries")

            # 학점 범위 검증
            if target_total < 0 or target_total > 30:
                print(f"DEBUG: 비정상적인 총 학점 요청: {target_total}")
                target_total = min(max(target_total, 0), 24)  # 0-24로 제한

            if target_major < 0 or target_major > 24:
                print(f"DEBUG: 비정상적인 전공 학점 요청: {target_major}")
                target_major = min(max(target_major, 0), 24)

            if target_elective < 0 or target_elective > 24:
                print(f"DEBUG: 비정상적인 교양 학점 요청: {target_elective}")
                target_elective = min(max(target_elective, 0), 24)
            
            # 전공 + 교양 학점이 총 학점을 초과하지 않도록 조정
            if target_major + target_elective > target_total:
                # 비율에 따라 조정
                ratio = target_total / (target_major + target_elective)
                target_major = int(target_major * ratio)
                target_elective = target_total - target_major
                print(f"DEBUG: 학점 조정됨 (초과) - 전공: {target_major}, 교양: {target_elective}")
            
            # 실제 목표 학점을 전공 + 교양 학점의 합으로 설정
            actual_total = target_major + target_elective
            if actual_total != target_total:
                print(f"DEBUG: 실제 목표 학점 조정 - 요청: {target_total}, 실제: {actual_total}")
                target_total = actual_total
            
            print("DEBUG: 최종 학점 설정 - total:", target_total, "major:", target_major, "elective:", target_elective)
        except ValueError:
            return JsonResponse({"error": "학점 파라미터가 올바르지 않습니다."}, status=500)

        print("DEBUG: free_days =", free_days)
        
        # 2) 신규: 시간 제약조건 파싱
        only_ranges = [json.loads(s) for s in request.GET.getlist('only_time_ranges[]')]
        avoid_times = [json.loads(s) for s in request.GET.getlist('avoid_times[]')]
        avoid_ranges = [json.loads(s) for s in request.GET.getlist('avoid_time_ranges[]')]
        
        # 특정 시간대 공강 파라미터 추가
        specific_avoid_times = [json.loads(s) for s in request.GET.getlist('specific_avoid_times[]')]
        specific_avoid_time_ranges = [json.loads(s) for s in request.GET.getlist('specific_avoid_time_ranges[]')]
        
        print("DEBUG: only_time_ranges =", only_ranges)
        print("DEBUG: avoid_times =", avoid_times)
        print("DEBUG: avoid_time_ranges =", avoid_ranges)
        print("DEBUG: specific_avoid_times =", specific_avoid_times)
        print("DEBUG: specific_avoid_time_ranges =", specific_avoid_time_ranges)

        # 3) 미리 추가된 과목 처리
        pre_added_courses = list(Courses.objects.filter(course_id__in=pre_added_ids))
        print("DEBUG: pre_added_courses count =", len(pre_added_courses))
        
        # 공강 요일에 대한 미리 추가된 과목 필터링
        if free_days:
            filtered = []
            for course in pre_added_courses:
                if not any(sch.day in free_days for sch in course.courseschedule_set.all()):
                    filtered.append(course)
            dropped = set(pre_added_ids) - set(c.course_id for c in filtered)
            if dropped:
                print("DEBUG: dropped pre_added courses on free_days:", dropped)
            pre_added_courses = filtered
            pre_added_ids = [c.course_id for c in pre_added_courses]

        # 3-3. 학생 정보 로드 (GraduationRecord 대신 UserProfile/Transcript 사용)
        student_id = request.user.id if request.user.is_authenticated else 1

        # UserProfile과 UserGraduationProgress 로드
        user_profile = None
        graduation_progress = []
        completed_courses = []

        if request.user.is_authenticated:
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if user_profile:
                # 졸업 진행 상황 로드
                graduation_progress = UserGraduationProgress.objects.filter(
                    user_profile=user_profile,
                    is_satisfied=False,
                    shortage_credits__gt=0
                ).select_related('category').order_by('-shortage_credits')

                # 이수한 과목 목록 로드 (Transcript에서)
                transcripts = Transcript.objects.filter(
                    user_profile=user_profile
                ).select_related('course')
                completed_courses = [t.course.course_name.strip().upper() for t in transcripts]

        # 학년 정보 (UserProfile에서)
        try:
            if user_profile and user_profile.current_grade:
                current_year = user_profile.current_grade
                if current_year >= 4:  # 4학년 이상은 전학년으로 처리
                    current_year = 100
            else:
                current_year = 3  # 기본값
        except Exception:
            current_year = 3
        print("DEBUG: current_year =", current_year)

        # UserProfile에서 학과 정보 가져오기
        if user_profile and user_profile.department:
            student_dept_id = user_profile.department.dept_id
            dept_name = user_profile.department.dept_name
            print(f"DEBUG: UserProfile에서 학과 정보 사용 - {dept_name} (ID: {student_dept_id})")
        else:
            student_dept_id = None
            dept_name = ""
            print("DEBUG: 학과 정보 없음 - 학과 필터링 비활성화")

        print("DEBUG: student_dept_id =", student_dept_id)
        


        # 이수한 과목 목록은 위에서 이미 처리됨
        print("DEBUG: completed_courses =", completed_courses[:5] if completed_courses else [])  # 처음 5개만 출력

        # 교양 세부 이수 상태 처리 (UserGraduationProgress에서)
        missing_gen_sub = {}
        if user_profile:
            # UserGraduationProgress에서 부족한 학점 정보 추출
            for progress in graduation_progress:
                if progress.shortage_credits > 0:
                    cat_name = progress.category.category_name
                    missing_gen_sub[cat_name] = int(progress.shortage_credits)
        print("DEBUG: missing_gen_sub =", missing_gen_sub)

        # 후보 강좌 조회 및 필터링
        candidate_qs = (
            (svc.course_search(year=year, term=term, category_name='전공') |
             svc.course_search(year=year, term=term, category_name='교양'))
            .annotate(upper_course_name=Upper('course_name'))
            .exclude(upper_course_name__in=[name.upper() for name in completed_courses])
        )

        # 졸업요건 기반 과목 우선순위 계산을 위한 맵 생성
        priority_map = {}
        
        if graduation_progress:
            for progress in graduation_progress:
                # 미충족 카테고리별로 부족 학점에 비례한 우선순위 부여
                category_id = progress.category_id
                shortage = float(progress.shortage_credits)
                priority_map[category_id] = min(shortage * 10, 100)  # 최대 100점
                print(f"DEBUG: 졸업요건 우선순위 - {progress.category.category_name}: {shortage}학점 부족 (우선순위: {priority_map[category_id]}점)")

        candidates = []
        for course in candidate_qs:
            # 제외할 과목 필터
            if exclude_names:
                should_exclude = False
                course_id_str = str(course.course_id)
                for exclude_item in exclude_names:
                    exclude_item_str = str(exclude_item).strip()
                    # 과목 코드로 정확히 매칭
                    if course_id_str == exclude_item_str:
                        should_exclude = True
                        print(f"DEBUG: 과목 제외됨 (ID 매칭) - '{course.course_name}' (ID: {course.course_id})")
                        break
                    # 과목명으로도 매칭
                    elif not exclude_item_str.isdigit():
                        course_name_lower = course.course_name.lower().strip()
                        exclude_name_lower = exclude_item_str.lower().strip()
                        if (course_name_lower == exclude_name_lower or 
                            exclude_name_lower in course_name_lower or 
                            course_name_lower in exclude_name_lower):
                            should_exclude = True
                            print(f"DEBUG: 과목 제외됨 (이름 매칭) - '{course.course_name}'")
                            break
                if should_exclude:
                    continue
            
            # 전공 과목 필터
            if course.category.category_name in ["전공필수", "전공선택"]:
                if course.target_year != "전학년":
                    try:
                        course_year = int(course.target_year[0])
                    except Exception:
                        course_year = 0
                    if course_year > current_year:
                        continue

                # 학과 매칭 - 관련 학과를 포함하도록 개선
                if course.category.category_name == "전공필수":
                    if not student_dept_id:
                        # 학생 학과 정보가 없으면 전공필수도 포함 (테스트용)
                        print(f"DEBUG: 전공필수 '{course.course_name}' 포함 - 학과 정보 없음 (테스트 모드)")
                        # continue를 주석처리하여 전공필수도 포함
                        pass

                    # 관련 학과 ID 목록 정의 (소프트웨어 관련)
                    # 소프트웨어학과(3), 소프트웨어학부(9)만 관련
                    related_dept_groups = [
                        {3, 9},  # 소프트웨어 관련 학과만
                    ]

                    # 학생 학과와 과목 학과가 같은 그룹에 속하는지 확인
                    is_related = False
                    for group in related_dept_groups:
                        if student_dept_id in group and course.dept_id in group:
                            is_related = True
                            break

                    # 학과 정보가 있는 경우에만 필터링
                    if student_dept_id:
                        # 같은 학과이거나 관련 학과가 아니면 제외
                        if course.dept_id != student_dept_id and not is_related:
                            # 다른 학과의 전공필수 제외
                            print(f"DEBUG: 전공필수 '{course.course_name}' 제외 - 관련없는 학과 과목 (과목 학과: {course.dept_id}, 학생 학과: {student_dept_id})")
                            continue
                        else:
                            print(f"DEBUG: 전공필수 '{course.course_name}' 포함 - 같은/관련 학과 (과목 학과: {course.dept_id}, 학생 학과: {student_dept_id})")

                elif course.category.category_name == "전공선택":
                    # 전공선택도 관련 학과 포함
                    if student_dept_id and course.dept_id:
                        # 관련 학과 ID 목록
                        related_dept_groups = [
                            {3, 9},  # 소프트웨어 관련 학과
                        ]

                        is_related = False
                        for group in related_dept_groups:
                            if student_dept_id in group and course.dept_id in group:
                                is_related = True
                                break

                        if course.dept_id != student_dept_id and not is_related:
                            print(f"DEBUG: 전공선택 '{course.course_name}' 제외 - 관련없는 학과 과목")
                            continue

            # 기본 필터
            if course.course_id in pre_added_ids:
                continue
            if course.credits <= 0:
                continue
            # 시간표 '00' slot 제거
            if any(sch.times.strip() == "00" for sch in course.courseschedule_set.all()):
                continue
            # Free-day 충돌
            if any(sch.day in free_days for sch in course.courseschedule_set.all()):
                continue
            # 교양은 target_year가 전학년이어야
            if get_effective_general_category(course) and course.target_year != "전학년":
                continue
            if any("가상강의실" in (sch.location or "") for sch in course.courseschedule_set.all()):
                continue
            # 교양 강좌 세부 항목 확인 및 초과 학점 과목 우선순위 조정
            if get_effective_general_category(course) and missing_gen_sub:
                effective_cat = get_effective_general_category(course)
                shortage = missing_gen_sub.get(effective_cat, 0)

                if shortage == 0:
                    # 이미 충족된 카테고리는 제외
                    continue
                elif course.credits > shortage:
                    # 필요한 학점보다 큰 과목은 우선순위 낮추기
                    # 예: 3학점 필요한데 4학점 과목인 경우
                    print(f"DEBUG: '{course.course_name}' ({course.credits}학점) > {effective_cat} 필요({shortage}학점) - 우선순위 감소")
                    # 나중에 priority_score에서 패널티 적용

            # 졸업요건 기반 우선순위 점수 계산
            priority_score = 0

            # 과목의 카테고리가 미충족 졸업요건에 해당하는지 확인
            if course.category_id in priority_map:
                priority_score = priority_map[course.category_id]
                print(f"DEBUG: '{course.course_name}' 졸업요건 우선순위 점수: {priority_score}")

            # 교양 과목이 필요 학점보다 큰 경우 패널티 적용
            if get_effective_general_category(course) and missing_gen_sub:
                effective_cat = get_effective_general_category(course)
                shortage = missing_gen_sub.get(effective_cat, 0)
                if shortage > 0 and course.credits > shortage:
                    # 초과 학점에 대한 패널티 (초과 학점 * 30점)
                    penalty = (course.credits - shortage) * 30
                    priority_score -= penalty
                    print(f"DEBUG: '{course.course_name}' 초과 학점 패널티 -{penalty}점 (필요: {shortage}, 실제: {course.credits})")

            # 전공필수 과목에 추가 가중치
            if course.category and course.category.category_name == "전공필수":
                priority_score += 30

            # 선호도 기반 점수 추가 (정규화된 점수 사용)
            preference_score = 0
            # 선호 교수 확인 (정규화된 점수)
            if course.instructor_name:
                if any(prof in course.instructor_name for prof in preferred_instructors):
                    preference_score += 100  # 500 → 100 (정규화)
                    print(f"DEBUG: 선호 교수 매칭 - {course.course_name} ({course.instructor_name}) +100점")
                if any(prof in course.instructor_name for prof in avoid_instructors):
                    preference_score -= 200  # 1000 → 200 (정규화)
                    print(f"DEBUG: 기피 교수 매칭 - {course.course_name} ({course.instructor_name}) -200점")

            # 선호 과목 확인 (정규화된 점수)
            if any(name.lower() in course.course_name.lower() for name in preferred_courses):
                preference_score += 100  # 500 → 100 (정규화)
                print(f"DEBUG: 선호 과목 매칭 - {course.course_name} +100점")

            # 기피 과목 제외 (avoid_courses에 추가)
            if any(name.lower() in course.course_name.lower() for name in avoid_courses):
                print(f"DEBUG: 기피 과목 제외 - {course.course_name}")
                continue

            # 교양 과목 태그 필터링
            if get_effective_general_category(course) and preference_tags:
                # 태그 매핑 (UI 태그 -> 필터링 로직)
                tag_filters = {
                    '#조별과제가 없는': lambda c: '팀' not in c.course_name and '조별' not in c.course_name,
                    '#과제가 적은': lambda c: '실습' not in c.course_name,
                    '#시험이 쉬운': lambda c: '심화' not in c.course_name and '고급' not in c.course_name,
                    '#출석 체크가 없는': lambda c: '실습' not in c.course_name and '실험' not in c.course_name,
                    '#온라인 강의': lambda c: '온라인' in c.course_name or '사이버' in c.course_name,
                    '#토론이 많은': lambda c: '토론' in c.course_name or '세미나' in c.course_name,
                    '#실습이 많은': lambda c: '실습' in c.course_name or '실험' in c.course_name,
                    '#이론 중심': lambda c: '이론' in c.course_name or '개론' in c.course_name
                }

                # 선택된 태그 중 하나라도 만족하지 못하면 제외
                tag_matched = False
                for tag in preference_tags:
                    if tag in tag_filters:
                        if tag_filters[tag](course):
                            tag_matched = True
                            preference_score += 20  # 태그 매칭 보너스
                            print(f"DEBUG: 태그 매칭 - {course.course_name} ({tag}) +20점")
                            break

                # 태그가 선택되었는데 하나도 매칭되지 않으면 선호도 감점
                if not tag_matched:
                    preference_score -= 10

            # 시간대 선호도
            if prefer_morning or prefer_afternoon:
                schedules = course.courseschedule_set.all()
                morning_count = 0
                afternoon_count = 0
                for sch in schedules:
                    times = [int(t) + 8 for t in sch.times.split(',') if t.strip().isdigit()]
                    for hour in times:
                        if hour < 12:
                            morning_count += 1
                        else:
                            afternoon_count += 1

                # 시간대 선호도 비율 기반 점수 (정규화)
                total_hours = morning_count + afternoon_count
                if total_hours > 0:
                    if prefer_morning:
                        morning_ratio = morning_count / total_hours
                        preference_score += int(morning_ratio * 100)  # 최대 100점 (정규화)
                        print(f"DEBUG: 오전 선호 - {course.course_name} 오전비율 {morning_ratio:.1%} +{int(morning_ratio * 100)}점")
                    elif prefer_afternoon:
                        afternoon_ratio = afternoon_count / total_hours
                        preference_score += int(afternoon_ratio * 100)  # 최대 100점 (정규화)
                        print(f"DEBUG: 오후 선호 - {course.course_name} 오후비율 {afternoon_ratio:.1%} +{int(afternoon_ratio * 100)}점")

            # 평점 기반 점수 계산 (정규화)
            rating_score = 0
            review_key = (course.course_name, course.instructor_name)
            if review_key in review_summaries:
                avg_rating = float(review_summaries[review_key].avg_rating)
                # 평점 구간별 점수 부여 (정규화: 0-100 범위)
                if avg_rating >= 4.5:
                    rating_score = 100  # 300 → 100
                elif avg_rating >= 4.0:
                    rating_score = 75   # 200 → 75
                elif avg_rating >= 3.5:
                    rating_score = 50   # 100 → 50
                elif avg_rating >= 3.0:
                    rating_score = 25   # 50 → 25
                else:
                    rating_score = 0
                print(f"DEBUG: 평점 적용 - {course.course_name} ({course.instructor_name}) 평점 {avg_rating:.2f} → +{rating_score}점")

            # 과목 정보에 우선순위 점수 추가 (나중에 활용)
            course.graduation_priority = priority_score
            course.preference_score = preference_score
            course.rating_score = rating_score  # 평점 점수 추가

            candidates.append(course)

        all_candidates = pre_added_courses + candidates
        print("DEBUG: candidates count =", len(candidates))
        print("DEBUG: all_candidates count =", len(all_candidates))

        # 각 후보 강좌의 스케줄 정보를 candidate_data에 저장
        candidate_data = []
        for course in all_candidates:
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
                'semester': "2025 1학기",
                'schedule': schedule_list,
                'location': locations[0] if locations else "",
                'pre_added': course.course_id in pre_added_ids
            }
            # 교양 강좌: effective_category 추가
            if get_effective_general_category(course):
                data_item['effective_category'] = get_effective_general_category(course)

            # 졸업요건 우선순위 점수 추가
            data_item['graduation_priority'] = getattr(course, 'graduation_priority', 0)
            data_item['preference_score'] = getattr(course, 'preference_score', 0)
            data_item['rating_score'] = getattr(course, 'rating_score', 0)  # 평점 점수 추가

            # 디버그: preference_score 확인
            if data_item['preference_score'] != 0:
                print(f"DEBUG: Course {course.course_name} has preference_score = {data_item['preference_score']}")

            # 디버그: rating_score 확인
            if data_item['rating_score'] != 0:
                print(f"DEBUG: Course {course.course_name} has rating_score = {data_item['rating_score']}")

            # 건물 번호 추출
            building_numbers = []
            for loc in locations:
                building = extract_building_number(loc)
                if building:
                    building_numbers.append(building)
            data_item['buildings'] = building_numbers

            candidate_data.append(data_item)
        
        print("DEBUG: candidate_data count =", len(candidate_data))

        # 시간 제약 조건 적용
        def in_range(h, start, end=None):
            return h >= start and (end is None or h < end)

        # only_time_ranges: 허용 범위 외 제거
        if only_ranges:
            filtered = []
            for d in candidate_data:
                ok = True
                for sched in d['schedule']:
                    hours = [int(t)+8 for t in sched['times'].split(',') if t.strip().isdigit()]
                    if not any(
                        sched['day'] in r['days']
                        and all(in_range(h, r['start_hour'], r.get('end_hour')) for h in hours)
                        for r in only_ranges
                    ):
                        ok = False
                        break
                if ok:
                    filtered.append(d)
            candidate_data = filtered
            print("DEBUG: only_time_ranges 적용 후 count =", len(candidate_data))

        # avoid_times / avoid_time_ranges: 회피 조건 제거
        if avoid_times or avoid_ranges:
            filtered = []
            for d in candidate_data:
                bad = False
                for sched in d['schedule']:
                    hours = [int(t)+8 for t in sched['times'].split(',') if t.strip().isdigit()]
                    if any(obj['day']==sched['day'] and h==obj['hour'] for obj in avoid_times for h in hours):
                        bad = True
                        break
                    if any(
                        sched['day'] in r['days']
                        and any(in_range(h, r['start_hour'], r.get('end_hour')) for h in hours)
                        for r in avoid_ranges
                    ):
                        bad = True
                        break
                if not bad:
                    filtered.append(d)
            candidate_data = filtered
            print("DEBUG: avoid_times/avoid_time_ranges 적용 후 count =", len(candidate_data))

        # specific_avoid_times / specific_avoid_time_ranges: 특정 요일+시간 회피
        if specific_avoid_times or specific_avoid_time_ranges:
            filtered = []
            for d in candidate_data:
                bad = False
                for sched in d['schedule']:
                    hours = [int(t)+8 for t in sched['times'].split(',') if t.strip().isdigit()]
                    
                    # 특정 요일+시간 회피
                    if any(obj['day']==sched['day'] and h==obj['hour'] 
                           for obj in specific_avoid_times for h in hours):
                        bad = True
                        break
                    
                    # 특정 요일+시간범위 회피
                    if any(
                        obj['day']==sched['day']
                        and any(h >= obj['start_hour'] and h < obj['end_hour'] for h in hours)
                        for obj in specific_avoid_time_ranges
                    ):
                        bad = True
                        break
                if not bad:
                    filtered.append(d)
            candidate_data = filtered
            print("DEBUG: specific_avoid_times/specific_avoid_time_ranges 적용 후 count =", len(candidate_data))

        # 동일학년 전공선택 강좌 우선 필터링
        for data in candidate_data:
            if data['category'] == '전공선택':
                if data['year'] == "전학년" or (
                    data['year'] and data['year'][0].isdigit() and int(data['year'][0]) == current_year
                ):
                    data['is_same_year'] = True
                else:
                    data['is_same_year'] = False

        pre_added_major = sum(
            data['credit'] for data in candidate_data
            if data['category'] in ['전공필수', '전공선택'] and data.get('pre_added', False)
        )
        
        if pre_added_major < target_major:
            needed_major = target_major - pre_added_major
            available_same_year_elective = sum(
                data['credit'] for data in candidate_data
                if data['category'] == '전공선택' and data.get('is_same_year', False) and not data.get('pre_added', False)
            )
            if available_same_year_elective >= needed_major:
                candidate_data = [
                    data for data in candidate_data
                    if not (data['category'] == '전공선택' and data.get('is_same_year') is False)
                ]
                print("DEBUG: 낮은학년 전공선택 과목 제거 후 candidate_data count =", len(candidate_data))

        # exclude_courses 적용
        if exclude_names:
            print("DEBUG: Applying exclude_courses filter:", exclude_names)
            filtered = []
            for d in candidate_data:
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
            
            candidate_data = filtered
            print("DEBUG: after exclude_courses filter:", len(candidate_data))

        # CP-SAT 모델 구성
        model = cp_model.CpModel()
        x = {}
        for data in candidate_data:
            x[data['id']] = model.NewBoolVar(f"course_{data['id']}")

        # 미리 추가된 과목 강제 포함
        for data in candidate_data:
            if data.get('pre_added', False):
                model.Add(x[data['id']] == 1)

        # 학점 제약 조건
        model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data) == target_total)
        model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data if
                      data['category'] in ['전공필수', '전공선택']) == target_major)
        model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data if
                      get_effective_general_category(course=DummyObj({'effective': data.get('effective_category', None)})) or
                      data['category'] not in ['전공필수', '전공선택']) == target_elective)

        # 교양 세부 카테고리별 상한 제약 추가 - 졸업요건 초과 방지
        if missing_gen_sub:
            print("DEBUG: 교양 세부 카테고리별 제약 추가 중...")
            for category_name, shortage_credits in missing_gen_sub.items():
                # 해당 카테고리의 과목들 찾기
                category_courses = [
                    data for data in candidate_data
                    if data.get('effective_category') == category_name
                ]

                if category_courses:
                    # 해당 카테고리 과목들의 학점 합이 부족분을 초과하지 않도록 제약
                    model.Add(
                        sum(data['credit'] * x[data['id']] for data in category_courses)
                        <= shortage_credits
                    )
                    print(f"DEBUG: {category_name} 카테고리 - 최대 {shortage_credits}학점 제약 추가 (과목 {len(category_courses)}개)")

        # 시간표 충돌 제약
        slot_mapping = defaultdict(list)
        for data in candidate_data:
            for sched in data['schedule']:
                day = sched['day']
                for t in sched['times'].split(","):
                    if t.strip().isdigit():
                        slot = int(t.strip()) + 8
                        slot_mapping[(day, slot)].append(data['id'])
        
        for (day, slot), ids in slot_mapping.items():
            model.Add(sum(x[cid] for cid in ids) <= 1)

        # 동일 강의명 제약
        name_groups = defaultdict(list)
        for data in candidate_data:
            name_groups[data['course_name']].append(data['id'])
        for name, ids in name_groups.items():
            model.Add(sum(x[cid] for cid in ids) <= 1)

        # 건물 간 이동시간 제약 (최적화된 버전)
        if max_walking_time < 20:  # 20은 "상관없음"을 의미
            # 시간-과목 매핑을 미리 구성 (성능 개선)
            time_course_map = defaultdict(lambda: defaultdict(list))

            for data in candidate_data:
                # 건물 정보가 있는 과목만 처리
                if not data.get('buildings'):
                    continue

                for sched in data['schedule']:
                    day = sched['day']
                    times = [int(t) + 8 for t in sched['times'].split(',') if t.strip().isdigit()]
                    for t in times:
                        time_course_map[day][t].append(data)

            # 중복 체크 방지용 세트
            checked_pairs = set()

            # 실제 수업이 있는 시간대만 처리
            for day in time_course_map:
                for hour in sorted(time_course_map[day].keys()):
                    # 다음 시간에도 수업이 있는 경우만 체크
                    if hour + 1 not in time_course_map[day]:
                        continue

                    curr_courses = time_course_map[day][hour]
                    next_courses = time_course_map[day][hour + 1]

                    # 연속된 시간에 수업이 있는 경우 거리 체크
                    for curr in curr_courses:
                        for next_c in next_courses:
                            if curr['id'] >= next_c['id']:  # 중복 체크 방지
                                continue

                            pair_key = (curr['id'], next_c['id'])
                            if pair_key in checked_pairs:
                                continue

                            # 두 과목의 건물 간 최대 거리 계산
                            max_distance = 0
                            for curr_bldg in curr.get('buildings', []):
                                for next_bldg in next_c.get('buildings', []):
                                    distance = get_building_distance(curr_bldg, next_bldg)
                                    max_distance = max(max_distance, distance)

                            if max_distance > max_walking_time:
                                model.Add(x[curr['id']] + x[next_c['id']] <= 1)
                                checked_pairs.add(pair_key)

        # 목적함수: 졸업요건 우선순위 + 선호도 + 평점 기반 최적화
        # 1. 졸업요건 충족도 (최우선)
        graduation_priority = sum(
            x[data['id']] * data.get('graduation_priority', 0)
            for data in candidate_data
        )

        # 2. 사용자 선호도 점수
        preference_priority = sum(
            x[data['id']] * data.get('preference_score', 0)
            for data in candidate_data
        )

        # 3. 강의 평점 점수 (새로 추가)
        rating_priority = sum(
            x[data['id']] * data.get('rating_score', 0)
            for data in candidate_data
        )

        # 4. 전공필수 우선
        required_priority = sum(
            x[data['id']] for data in candidate_data
            if data['category'] == '전공필수' and (
                data['year'] == "전학년" or (data['year'][0].isdigit() and int(data['year'][0]) <= current_year)
            )
        )

        # 5. 동일학년 전공선택 우선
        elective_priority = sum(
            x[data['id']] for data in candidate_data
            if data['category'] == '전공선택' and (
                data['year'] == "전학년" or (data['year'][0].isdigit() and int(data['year'][0]) == current_year)
            )
        )

        # 6. 시간표 밀집도 계산 및 적용
        compactness_bonus = 0
        if prefer_compact:
            # 각 요일별 수업 분포 계산
            daily_classes = defaultdict(list)
            for data in candidate_data:
                for sch in data['schedule']:
                    day = sch['day']
                    times = [int(t) + 8 for t in sch['times'].split(',') if t.strip().isdigit()]
                    for t in times:
                        daily_classes[day].append((t, data['id']))

            # 밀집도 보너스 계산 (공강이 적을수록 높은 점수)
            for day, time_list in daily_classes.items():
                if time_list:
                    times = sorted([t for t, _ in time_list])
                    if len(times) > 1:
                        gaps = sum(times[i+1] - times[i] - 1 for i in range(len(times)-1))
                        # 공강이 적을수록 보너스 (최대 200점/요일)
                        day_bonus = max(0, 200 - gaps * 50)
                        for _, course_id in time_list:
                            compactness_bonus += x[course_id] * day_bonus

            print(f"DEBUG: 밀집도 선호 활성화 - 공강 최소화 보너스 적용")

        # 최종 목적함수 (균형 개선: 사용자 선호도 중시)
        # 개선: 졸업요건은 여전히 우선이지만 사용자 선호도와 다른 요소들도 실질적으로 반영
        model.Maximize(
            graduation_priority * 3000 +    # 10000 → 3000 (여전히 최우선이지만 균형있게)
            preference_priority * 2000 +    # 1000 → 2000 (사용자 선호도 중요성 상향)
            rating_priority * 1500 +        # 2000 → 1500 (평점은 중요하지만 선호도보다 낮게)
            compactness_bonus * 800 +       # 500 → 800 (밀집도 영향력 증가)
            required_priority * 1000 +      # 1000 유지 (전공필수 중요도 유지)
            elective_priority * 600         # 500 → 600 (전공선택 약간 상향)
        )
        print(f"DEBUG: 목적함수 가중치 - 졸업:3000, 선호도:2000, 평점:1500, 밀집도:800, 전필:1000, 전선:600")

        # Phase 1: 최적 목적함수 값 찾기
        solver = cp_model.CpSolver()
        # 솔버 파라미터 최적화
        solver.parameters.max_time_in_seconds = 5  # 최대 5초
        solver.parameters.num_search_workers = 4   # 병렬 처리
        solver.parameters.linearization_level = 2  # 선형화 레벨

        print("DEBUG: Starting Phase 1 optimization...")
        print(f"DEBUG: 후보 과목 수: {len(candidate_data)}개")
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return JsonResponse({"error": "해결책을 찾지 못했습니다."}, status=500)

        best_value = solver.ObjectiveValue()
        print("DEBUG: Phase 1 Best objective =", best_value)

        # 디버그: 목적함수 구성요소 출력
        grad_val = sum(solver.Value(x[data['id']]) * data.get('graduation_priority', 0) for data in candidate_data)
        pref_val = sum(solver.Value(x[data['id']]) * data.get('preference_score', 0) for data in candidate_data)
        rating_val = sum(solver.Value(x[data['id']]) * data.get('rating_score', 0) for data in candidate_data)  # 평점 점수 합계
        req_val = sum(solver.Value(x[data['id']]) for data in candidate_data
                     if data['category'] == '전공필수' and (data['year'] == "전학년" or (
                         data['year'][0].isdigit() and int(data['year'][0]) <= current_year)))
        elec_val = sum(solver.Value(x[data['id']]) for data in candidate_data
                      if data['category'] == '전공선택' and (data['year'] == "전학년" or (
                          data['year'][0].isdigit() and int(data['year'][0]) == current_year)))

        # 선택된 과목들의 평균 평점 계산
        selected_with_ratings = []
        for data in candidate_data:
            if solver.Value(x[data['id']]) == 1 and data.get('rating_score', 0) > 0:
                # rating_score를 원래 평점으로 역산
                rating_score = data.get('rating_score', 0)
                if rating_score >= 300:
                    avg_rating = 4.5
                elif rating_score >= 200:
                    avg_rating = 4.0
                elif rating_score >= 100:
                    avg_rating = 3.5
                elif rating_score >= 50:
                    avg_rating = 3.0
                else:
                    avg_rating = 2.5
                selected_with_ratings.append(avg_rating)
                print(f"DEBUG: Selected with rating - {data['course_name']} (평점 {avg_rating:.1f})")

        if selected_with_ratings:
            avg_of_selected = sum(selected_with_ratings) / len(selected_with_ratings)
            print(f"DEBUG: 선택된 과목 중 평점이 있는 과목들의 평균 평점: {avg_of_selected:.2f}")

        print(f"DEBUG: Phase 1 components - Graduation: {grad_val}, Preference: {pref_val}, Rating: {rating_val}, Required: {req_val}, Elective: {elec_val}")
        print(f"DEBUG: Phase 1 calculated objective = {grad_val * 100000 + pref_val * 10000 + rating_val * 5000 + req_val * 100 + elec_val * 10}")

        # Phase 2: 최적값을 강제하고 모든 해 찾기
        model2 = cp_model.CpModel()
        x2 = {}
        for data in candidate_data:
            x2[data['id']] = model2.NewBoolVar(f"course2_{data['id']}")

        # 제약 조건 동일하게 적용
        for data in candidate_data:
            if data.get('pre_added', False):
                model2.Add(x2[data['id']] == 1)

        model2.Add(sum(data['credit'] * x2[data['id']] for data in candidate_data) == target_total)
        model2.Add(sum(data['credit'] * x2[data['id']] for data in candidate_data if
                      data['category'] in ['전공필수', '전공선택']) == target_major)
        model2.Add(sum(data['credit'] * x2[data['id']] for data in candidate_data if
                      get_effective_general_category(course=DummyObj({'effective': data.get('effective_category', None)})) or
                      data['category'] not in ['전공필수', '전공선택']) == target_elective)

        # Phase 2에도 교양 세부 카테고리별 상한 제약 추가
        if missing_gen_sub:
            for category_name, shortage_credits in missing_gen_sub.items():
                category_courses = [
                    data for data in candidate_data
                    if data.get('effective_category') == category_name
                ]
                if category_courses:
                    model2.Add(
                        sum(data['credit'] * x2[data['id']] for data in category_courses)
                        <= shortage_credits
                    )

        for (day, slot), ids in slot_mapping.items():
            model2.Add(sum(x2[cid] for cid in ids) <= 1)
        for name, ids in name_groups.items():
            model2.Add(sum(x2[cid] for cid in ids) <= 1)
        
        # 건물 간 이동시간 제약 (Phase 2에도 최적화 적용)
        if max_walking_time < 20:
            # Phase 1에서 이미 계산한 time_course_map 재사용
            if 'time_course_map' not in locals():
                time_course_map = defaultdict(lambda: defaultdict(list))
                for data in candidate_data:
                    if not data.get('buildings'):
                        continue
                    for sched in data['schedule']:
                        day = sched['day']
                        times = [int(t) + 8 for t in sched['times'].split(',') if t.strip().isdigit()]
                        for t in times:
                            time_course_map[day][t].append(data)

            checked_pairs = set()
            for day in time_course_map:
                for hour in sorted(time_course_map[day].keys()):
                    if hour + 1 not in time_course_map[day]:
                        continue

                    curr_courses = time_course_map[day][hour]
                    next_courses = time_course_map[day][hour + 1]

                    for curr in curr_courses:
                        for next_c in next_courses:
                            if curr['id'] >= next_c['id']:
                                continue
                            pair_key = (curr['id'], next_c['id'])
                            if pair_key in checked_pairs:
                                continue

                            max_distance = 0
                            for curr_bldg in curr.get('buildings', []):
                                for next_bldg in next_c.get('buildings', []):
                                    distance = get_building_distance(curr_bldg, next_bldg)
                                    max_distance = max(max_distance, distance)

                            if max_distance > max_walking_time:
                                model2.Add(x2[curr['id']] + x2[next_c['id']] <= 1)
                                checked_pairs.add(pair_key)

        # 최적 목적함수 값 강제 (Phase 1과 동일한 계산 사용)
        # 1. 졸업요건 충족도
        grad_sum = sum(x2[data['id']] * data.get('graduation_priority', 0) for data in candidate_data)

        # 2. 사용자 선호도
        pref_sum = sum(x2[data['id']] * data.get('preference_score', 0) for data in candidate_data)

        # 4. 전공필수 우선
        req_sum = sum(x2[data['id']] for data in candidate_data
                     if data['category'] == '전공필수' and (data['year'] == "전학년" or (
                         data['year'][0].isdigit() and int(data['year'][0]) <= current_year)))

        # 4. 동일학년 전공선택 우선
        elec_sum = sum(x2[data['id']] for data in candidate_data
                      if data['category'] == '전공선택' and (data['year'] == "전학년" or (
                          data['year'][0].isdigit() and int(data['year'][0]) == current_year)))

        # Phase 2: 일단 목적함수 제약 없이 모든 유효한 해 찾기
        # 목적함수 제약을 제거하여 실제로 해가 존재하는지 확인
        print(f"DEBUG: Phase 2 - Searching for ALL valid solutions (no objective constraint)")
        print(f"DEBUG: Phase 1 found solution with objective = {best_value}")

        # 디버그: Phase 2 목적함수 구성요소 계산 확인
        print("DEBUG: Phase 2 objective components checking:")
        total_grad = sum(data.get('graduation_priority', 0) for data in candidate_data)
        total_pref = sum(data.get('preference_score', 0) for data in candidate_data)
        print(f"  Total possible grad priority: {total_grad}")
        print(f"  Total possible pref score: {total_pref}")

        # 해 수집기
        class TimetableSolutionCollector(cp_model.CpSolverSolutionCallback):
            def __init__(self, x, candidate_data, limit):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self._x = x
                self._candidate_data = {d['id']: d for d in candidate_data}
                self._limit = limit
                self._solutions = []
                self._solution_count = 0

            def OnSolutionCallback(self):
                self._solution_count += 1
                print(f"DEBUG: [Phase 2] Found solution #{self._solution_count}")
                if self._solution_count > self._limit:
                    self.StopSearch()
                    return

                solution = []
                for cid, var in self._x.items():
                    if self.Value(var) == 1:
                        data = self._candidate_data[cid]
                        solution.append({
                            'course_id': data['id'],
                            'course_name': data.get('course_name', ''),
                            'course_code': data.get('course_code', ''),
                            'section': data.get('section', ''),
                            'credits': data.get('credit', 0),
                            'target_year': data.get('year', ''),
                            'instructor_name': data.get('instructor_name', ''),
                            'capacity': data.get('capacity', 0),
                            'dept_name': data.get('dept_name', ''),
                            'category_name': data.get('category', ''),
                            'semester': data.get('semester', ''),
                            'schedules': data.get('schedule', []),
                            'location': data.get('location', '')
                        })
                self._solutions.append(solution)

            def Solutions(self):
                return self._solutions

        # Phase 2: 여러 개의 다른 해 찾기 (SearchForAllSolutions 대신 직접 구현)
        timetables_data = []
        solver2 = cp_model.CpSolver()
        solver2.parameters.max_time_in_seconds = 1  # 각 해당 1초 제한
        solver2.parameters.num_search_workers = 4

        print("DEBUG: Starting Phase 2 search for multiple solutions...")

        # 최대 20개의 서로 다른 시간표 찾기
        for i in range(20):
            status = solver2.Solve(model2)

            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                solution = []
                selected_ids = []

                for data in candidate_data:
                    if solver2.Value(x2[data['id']]) == 1:
                        selected_ids.append(data['id'])

                        # 평점 정보 조회
                        avg_rating = None
                        review_key = (data.get('course_name', ''), data.get('instructor_name', ''))
                        if review_key in review_summaries and review_key[0] and review_key[1]:
                            avg_rating = float(review_summaries[review_key].avg_rating)

                        solution.append({
                            'course_id': data['id'],
                            'course_name': data.get('course_name', ''),
                            'course_code': data.get('course_code', ''),
                            'section': data.get('section', ''),
                            'credits': data.get('credit', 0),
                            'target_year': data.get('year', ''),
                            'instructor_name': data.get('instructor_name', ''),
                            'capacity': data.get('capacity', 0),
                            'dept_name': data.get('dept_name', ''),
                            'category_name': data.get('category', ''),
                            'semester': data.get('semester', ''),
                            'schedules': data.get('schedule', []),
                            'location': data.get('location', ''),
                            'avg_rating': avg_rating  # 평점 정보 추가
                        })

                timetables_data.append(solution)
                print(f"DEBUG: Found solution #{i+1} with {len(solution)} courses")

                # 다음 반복에서 같은 해를 찾지 않도록 제약 추가
                # 선택된 과목 중 적어도 하나는 다르게 선택하도록 함
                model2.Add(sum(x2[cid] for cid in selected_ids) < len(selected_ids))
            else:
                print(f"DEBUG: No more solutions found after {i} iterations")
                break

        print(f"DEBUG: Phase 2 search finished. Total solutions: {len(timetables_data)}")

        # 평점 데이터 요약 출력
        if review_summaries:
            print(f"\nDEBUG: === 강의 평점 데이터 요약 ===")
            print(f"  로드된 평점 데이터: {len(review_summaries)}개")
            ratings_applied = sum(1 for data in candidate_data if data.get('rating_score', 0) > 0)
            print(f"  평점이 적용된 후보 과목: {ratings_applied}개")
            if ratings_applied > 0:
                avg_rating_score = sum(data.get('rating_score', 0) for data in candidate_data if data.get('rating_score', 0) > 0) / ratings_applied
                print(f"  평균 평점 점수: {avg_rating_score:.1f}점")
            print("================================\n")

        # 선호도 파라미터 요약 출력
        if preferred_instructors or avoid_instructors or preferred_courses or avoid_courses or preference_tags:
            print("\nDEBUG: === 사용자 선호도 요약 ===")
            if preferred_instructors:
                print(f"  선호 교수: {', '.join(preferred_instructors)}")
            if avoid_instructors:
                print(f"  기피 교수: {', '.join(avoid_instructors)}")
            if preferred_courses:
                print(f"  선호 과목: {', '.join(preferred_courses)}")
            if avoid_courses:
                print(f"  기피 과목: {', '.join(avoid_courses)}")
            if preference_tags:
                print(f"  교양 태그: {', '.join(preference_tags)}")
            if prefer_morning:
                print("  오전 수업 선호")
            if prefer_afternoon:
                print("  오후 수업 선호")
            if prefer_compact:
                print("  밀집 시간표 선호")
            print(f"  최대 이동시간: {max_walking_time}분")
            print("================================\n")

        # ========== 선호도 기반 시간표 정렬 및 필터링 ==========
        print("DEBUG: Starting preference-based sorting and filtering...")

        def calculate_timetable_preference_score(timetable, prefs):
            """시간표의 선호도 점수 계산"""
            score = 0
            matched_prefs = {'instructors': 0, 'courses': 0, 'avoided': 0}

            for course in timetable:
                instructor = course.get('instructor_name', '')
                course_name = course.get('course_name', '')

                # 선호 교수 점수 (정규화된 점수 사용)
                if instructor and prefs.get('preferred_instructors'):
                    for pref in prefs['preferred_instructors']:
                        if pref in instructor:
                            score += 100  # 1000 → 100 (정규화)
                            matched_prefs['instructors'] += 1
                            print(f"  DEBUG: 선호 교수 매칭 +100: {course_name} ({instructor})")

                # 기피 교수 감점 (정규화된 점수 사용)
                if instructor and prefs.get('avoid_instructors'):
                    for avoid in prefs['avoid_instructors']:
                        if avoid in instructor:
                            score -= 200  # 2000 → 200 (정규화)
                            matched_prefs['avoided'] += 1
                            print(f"  DEBUG: 기피 교수 발견 -200: {course_name} ({instructor})")

                # 선호 과목 점수 (정규화된 점수 사용)
                if prefs.get('preferred_courses'):
                    for pref in prefs['preferred_courses']:
                        if pref.lower() in course_name.lower():
                            score += 100  # 1000 → 100 (정규화)
                            matched_prefs['courses'] += 1
                            print(f"  DEBUG: 선호 과목 매칭 +100: {course_name}")

                # 기피 과목 감점 (정규화된 점수 사용)
                if prefs.get('avoid_courses'):
                    for avoid in prefs['avoid_courses']:
                        if avoid.lower() in course_name.lower():
                            score -= 200  # 2000 → 200 (정규화)
                            matched_prefs['avoided'] += 1
                            print(f"  DEBUG: 기피 과목 발견 -200: {course_name}")

                # 시간대 선호도
                if prefs.get('prefer_morning') or prefs.get('prefer_afternoon'):
                    schedules = course.get('schedules', [])
                    morning_count = 0
                    afternoon_count = 0

                    for sch in schedules:
                        times = sch.get('times', '')
                        if times:
                            for t in times.split(','):
                                if t.strip().isdigit():
                                    hour = int(t) + 8
                                    if hour < 12:
                                        morning_count += 1
                                    else:
                                        afternoon_count += 1

                    if prefs.get('prefer_morning') and morning_count > afternoon_count:
                        score += 50  # 200 → 50 (정규화)
                    elif prefs.get('prefer_afternoon') and afternoon_count > morning_count:
                        score += 50  # 200 → 50 (정규화)

            return score, matched_prefs

        # 선호도 정보 수집
        preferences = {
            'preferred_instructors': preferred_instructors,
            'avoid_instructors': avoid_instructors,
            'preferred_courses': preferred_courses,
            'avoid_courses': avoid_courses,
            'prefer_morning': prefer_morning,
            'prefer_afternoon': prefer_afternoon
        }

        # 각 시간표에 선호도 점수 계산 및 추가
        scored_timetables = []
        for idx, timetable in enumerate(timetables_data):
            print(f"\nDEBUG: 시간표 #{idx+1} 선호도 평가:")
            score, matched = calculate_timetable_preference_score(timetable, preferences)

            # 시간표에 메타데이터 추가
            timetable_with_score = {
                'courses': timetable,
                'preference_score': score,
                'matched_preferences': matched,
                'recommendation_level': '★★★★★' if score > 3000 else '★★★★' if score > 1500 else '★★★' if score > 0 else '★★' if score >= -1000 else '★'
            }
            scored_timetables.append((score, timetable_with_score, timetable))
            print(f"  총 선호도 점수: {score}점")

        # 선호도 점수로 정렬 (높은 점수가 먼저)
        scored_timetables.sort(key=lambda x: x[0], reverse=True)

        # 정렬된 시간표 리스트 생성
        sorted_timetables = [t[2] for t in scored_timetables]  # 원본 형식 유지

        # 최고/최저 점수 출력
        if scored_timetables:
            best_score = scored_timetables[0][0]
            worst_score = scored_timetables[-1][0]
            print(f"\nDEBUG: 선호도 점수 범위: {worst_score}점 ~ {best_score}점")
            print(f"DEBUG: 최고 점수 시간표가 첫 번째로 배치됨 (점수: {best_score})")

        print("DEBUG: Total unique solutions found:", len(sorted_timetables))
        print("DEBUG: --- Timetable Generation End ---")

        result = {
            'progress': '완료',
            'found': len(sorted_timetables),
            'timetables': sorted_timetables,
            'message': f"선호도 순으로 정렬된 {len(sorted_timetables)}개의 시간표를 찾았습니다." if sorted_timetables else "조건에 맞는 시간표를 찾지 못했습니다. 조건을 변경해보세요."
        }

        def event_stream():
            yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"

        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


def manage_view(request):
    """시간표 관리 페이지 - 저장된 시간표 목록 조회"""
    user_id = request.user.id if request.user.is_authenticated else 8
    saved_timetables = SavedTimetable.objects.filter(user_id=user_id).order_by('-created_at')
    
    print(f"사용자 {user_id}의 저장된 시간표 개수: {saved_timetables.count()}")
    
    timetables_data = []
    for timetable in saved_timetables:
        courses = []
        
        # 시간표의 모든 과목 가져오기
        for course in timetable.courses.all():
            course_data = {
                'course_id': course.course_id,
                'course_name': course.course_name,
                'credit': course.credits,
                'category': course.category,
                'location': course.location,
                'schedules': []
            }
            
            # 각 과목의 스케줄 정보 가져오기
            for schedule in course.schedules.all():
                course_data['schedules'].append({
                    'day': schedule.day_of_week,
                    'times': schedule.time_slots,
                    'start_time': schedule.start_time,
                    'end_time': schedule.end_time,
                    'location': schedule.location
                })
            
            courses.append(course_data)
        
        timetables_data.append({
            'id': timetable.id,
            'title': timetable.title,
            'created_at': timetable.created_at.strftime('%Y-%m-%d %H:%M'),
            'total_credits': timetable.total_credits,
            'major_credits': timetable.major_credits,
            'elective_credits': timetable.elective_credits,
            'courses': courses
        })
        
        print(f"시간표 로드됨: {timetable.title} ({len(courses)}개 과목)")
    
    # JSON 문자열로 변환
    timetables_json = json.dumps(timetables_data, ensure_ascii=False)
    
    print(f"JSON 데이터 크기: {len(timetables_json)} 문자")

    current_user = {
        'user_id': request.user.id if request.user.is_authenticated else 0,
        'username': request.user.username if request.user.is_authenticated else '익명',
        'first_name': request.user.first_name if request.user.is_authenticated else '',
        'last_name': request.user.last_name if request.user.is_authenticated else '',
        'is_authenticated': bool(request.user.is_authenticated),
    }
    current_user_json = json.dumps(current_user, ensure_ascii=False)
    
    return render(request, "home/manage.html", {
        'timetables': timetables_data,
        'timetables_json': timetables_json,
        'current_user_json': current_user_json,
    })


@csrf_exempt
def save_timetable(request):
    """시간표 저장 API"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST 요청만 허용됩니다.'}, status=405)
    
    try:
        data = json.loads(request.body)
        courses = data.get('courses', [])
        title = data.get('title', '')
        
        print(f"시간표 저장 요청 받음: {len(courses)}개 과목")
        
        # 사용자 정보 가져오기
        user_id = request.user.id if request.user.is_authenticated else 8
        print(f"사용자 ID: {user_id}")
        
        # 시간표 제목 자동 생성
        if not title or title == '새 시간표':
            count = SavedTimetable.objects.filter(user_id=user_id).count()
            title = f"시간표 {count + 1}"
        
        # 학점 계산
        total_credits = sum(course.get('credit', 0) for course in courses)
        major_credits = sum(course.get('credit', 0) for course in courses 
                          if course.get('category', '') in ['전공필수', '전공선택'])
        elective_credits = total_credits - major_credits
        
        print(f"계산된 학점 - 총: {total_credits}, 전공: {major_credits}, 교양: {elective_credits}")
        
        # 시간표 메인 레코드 생성
        timetable = SavedTimetable.objects.create(
            user_id=user_id,
            title=title,
            semester_year=2025,
            semester_term='1학기',
            total_credits=total_credits,
            major_credits=major_credits,
            elective_credits=elective_credits
        )
        
        print(f"시간표 메인 레코드 생성됨: ID {timetable.id}")
        
        # 시간표 상세 정보 저장
        for course_data in courses:
            course_id = course_data.get('course_id')
            course_name = course_data.get('course_name', '')
            credits = course_data.get('credit', 0)
            category = course_data.get('category', '')
            schedules = course_data.get('schedules', [])
            
            print(f"과목 저장 중: {course_name} ({credits}학점)")
            
            # 첫 번째 스케줄의 location을 기본 location으로 사용
            default_location = ''
            if schedules and len(schedules) > 0:
                default_location = schedules[0].get('location', '')
            
            # 과목 정보 저장
            timetable_course = SavedTimetableCourse.objects.create(
                timetable=timetable,
                course_id=course_id,
                course_name=course_name,
                credits=credits,
                category=category,
                location=default_location,
                user_note=course_data.get('note', ''),
                custom_color=course_data.get('color', '')
            )
            
            print(f"과목 레코드 생성됨: ID {timetable_course.id}")
            
            # 스케줄 정보 저장
            for schedule in schedules:
                day = schedule.get('day', '')
                times = schedule.get('times', '')
                schedule_location = schedule.get('location', default_location)
                
                print(f"스케줄 처리 중: {day} {times} @ {schedule_location}")
                
                # 시작/종료 시간 계산
                if times:
                    try:
                        time_slots = times.split(',')
                        if time_slots:
                            start_hour = int(time_slots[0]) + 8  # 02 -> 10시
                            end_hour = int(time_slots[-1]) + 9   # 04 -> 13시
                            start_time = f"{start_hour:02d}:00"
                            end_time = f"{end_hour:02d}:00"
                        else:
                            start_time = "09:00"
                            end_time = "10:00"
                    except (ValueError, IndexError) as e:
                        print(f"시간 파싱 오류: {e}, times: {times}")
                        start_time = "09:00"
                        end_time = "10:00"
                        times = "01"
                else:
                    start_time = "09:00"
                    end_time = "10:00"
                    times = "01"
                
                schedule_record = SavedTimetableSchedule.objects.create(
                    timetable_course=timetable_course,
                    day_of_week=day,
                    start_time=start_time,
                    end_time=end_time,
                    time_slots=times,
                    location=schedule_location
                )
                
                print(f"스케줄 저장됨: ID {schedule_record.id} - {day} {start_time}-{end_time}")
        
        print(f"시간표 저장 완료: {timetable.title}")
        
        return JsonResponse({
            'success': True,
            'timetable_id': timetable.id,
            'title': timetable.title,
            'message': '시간표가 성공적으로 저장되었습니다.'
        })
        
    except Exception as e:
        print(f"시간표 저장 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'시간표 저장 중 오류가 발생했습니다: {str(e)}'}, status=500)


@csrf_exempt
def delete_timetable(request, timetable_id):
    """시간표 삭제 API"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'DELETE 요청만 허용됩니다.'}, status=405)
    
    try:
        user_id = request.user.id if request.user.is_authenticated else 8
        timetable = SavedTimetable.objects.filter(
            id=timetable_id,
            user_id=user_id
        ).first()
        
        if not timetable:
            return JsonResponse({'error': '시간표를 찾을 수 없습니다.'}, status=404)
        
        print(f"시간표 삭제: {timetable.title} (ID: {timetable_id})")
        timetable.delete()
        
        return JsonResponse({
            'success': True,
            'message': '시간표가 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        print(f"시간표 삭제 오류: {str(e)}")
        return JsonResponse({'error': f'시간표 삭제 중 오류가 발생했습니다: {str(e)}'}, status=500) 