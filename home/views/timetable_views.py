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
    시간표 생성 메인 함수 (리팩토링 버전)
    사용자 제약조건을 기반으로 최적의 시간표 조합을 생성
    CP-SAT 알고리즘을 사용하여 최적화 문제를 해결
    """
    try:
        # 서비스 초기화
        from home.services.parameter_parser import ParameterParser
        from home.services.timetable_generation_service import TimetableGenerationService

        # 1. 파라미터 파싱
        parser = ParameterParser()
        timetable_request = parser.parse_request(request)

        # 2. 시간표 생성 서비스 실행
        service = TimetableGenerationService()
        result = service.generate(request.user, timetable_request)

        # 3. 응답 반환
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
