from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from .models import Course
import json, random

def course_serach_test_view(request):
    return render(request, 'home/search_test.html')

def timetable_view(request):
    # ✅ 강의 유형별 필터링
    major_required = Course.objects.filter(course_type='전공필수').order_by('course_name')
    major_elective = Course.objects.filter(course_type='전공선택').order_by('course_name')
    general_elective = Course.objects.filter(course_type='교양선택').order_by('course_name')
    free_elective = Course.objects.filter(course_type='일반선택').order_by('course_name')
    teaching_required = Course.objects.filter(course_type='교직필수').order_by('course_name')

    return render(request, 'home/timetable.html', {
        'major_required': major_required,
        'major_elective': major_elective,
        'general_elective': general_elective,
        'free_elective': free_elective,
        'teaching_required': teaching_required
    })

def login_view(request):
    return render(request, 'home/login.html')

def dashboard_view(request):
    return render(request, 'home/dashboard.html')


def generate_timetable(request):
    # ✅ 모든 강의 가져오기
    courses = list(Course.objects.all())  

    # ✅ 생성할 시간표 개수
    NUM_TIMETABLES = 3
    DAYS = ["월", "화", "수", "목", "금"]
    TIMES = list(range(8, 20))  # 오전 8시 ~ 오후 8시

    if len(courses) < 10:
        return JsonResponse({"error": "강의 데이터가 부족합니다."}, status=400)

    generated_timetables = []
    for _ in range(NUM_TIMETABLES):
        random.shuffle(courses)  
        selected_courses = courses[:6]  # ✅ 랜덤으로 6개의 강의 선택

        timetable_data = []
        occupied_slots = set()  # ✅ 중복된 시간 방지

        for course in selected_courses:
            day = random.choice(DAYS)  # ✅ 랜덤 요일 선택
            start_time = random.choice(TIMES)  # ✅ 랜덤 시작 시간 선택
            end_time = start_time + 1  # ✅ 1시간 강의로 설정

            # ✅ 중복 체크: 이미 같은 시간대에 강의가 있다면 다른 시간 찾기
            attempt = 0
            while (day, start_time) in occupied_slots and attempt < 10:
                day = random.choice(DAYS)
                start_time = random.choice(TIMES)
                attempt += 1
            
            occupied_slots.add((day, start_time))  # ✅ 예약된 시간 저장

            timetable_data.append({
                "course_code": course.course_code,
                "course_name": course.course_name,
                "day": day,
                "times": f"{start_time}:00-{end_time}:00",
                "location": f"{random.randint(101, 305)}호"  # ✅ 랜덤 강의실
            })

        generated_timetables.append(timetable_data)

    return JsonResponse({"timetables": generated_timetables})


