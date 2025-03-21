import time
import json
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render
from django.db import models
from .models import Course, CourseSchedule

def generate_timetable_stream(request):
    """
    새로운 시간표 생성 알고리즘 프로토타입.
    
    우선순위 및 제약 조건:
      1. 사용자가 선택한 공강요일(free_days)에 해당하는 강의는 후보에서 제외 (단, 미리 추가한 강좌는 예외)
      2. 미리 시간표에 추가한 강좌(existing_courses)은 반드시 포함
      3. 같은 과목명(course_name)의 강좌는 한 시간표에 중복 포함 불가
      4. 시간표에 포함된 강좌들의 학점 합이 사용자가 입력한 총학점, 전공학점, 교양학점과 정확히 일치해야 함  
         - 전공: 전공필수, 전공선택  
         - 교양: 교양선택  
      5. 0학점 강좌, 스케줄 정보가 아예 없거나 course_schedule의 times 값이 "00"인 강좌는 후보에서 제외  
      
    최종적으로 조건을 만족하는 시간표 후보(최대 50개)를 JSON 형식으로 SSE(Server-Sent Events)로 전달합니다.
    """
    # 1. GET 파라미터 파싱: free_days, existing_courses, 그리고 학점 조건
    free_days = request.GET.getlist('free_days[]')
    existing_course_ids = request.GET.getlist('existing_courses[]')
    try:
        pre_added_ids = [int(cid) for cid in existing_course_ids]
    except ValueError:
        pre_added_ids = []
    try:
        target_total = int(request.GET.get('total_credits', 18))
        target_major = int(request.GET.get('major_credits', 9))
        target_elective = int(request.GET.get('elective_credits', 9))
    except ValueError:
        return JsonResponse({"error": "학점 파라미터가 올바르지 않습니다."}, status=400)
    
    # 미리 추가한 강좌는 반드시 포함
    pre_added_courses = list(Course.objects.filter(course_id__in=pre_added_ids))
    
    # 하드코딩: 소프트웨어학부(dept_id=2) / 25년도 1학기(semester_id=21)
    student_dept_id = 2
    semester_id_filter = 21
    
    # 2. 학생의 현재 수강 내역 (dummy 처리: 아직 수강한 강좌 없음)
    completed_courses_ids = []  # 추후 실제 내역이 있다면 해당 course_id들을 여기에 포함
    
    # 3. 후보 강좌 조회 (조건: 이번 학기, 전공/교양 강좌)
    candidate_qs = Course.objects.filter(semester_id=semester_id_filter, 
                                         course_type__in=['전공필수', '전공선택', '교양선택'])
    candidates = []
    for course in candidate_qs:
        # 이미 수강한 강좌는 제외
        if course.course_id in completed_courses_ids:
            continue
        # 미리 추가된 강좌는 이미 pre_added_courses에 있으므로 후보에서 제외
        if course.course_id in pre_added_ids:
            continue
        # 0학점 강좌는 제외
        if course.credit <= 0:
            continue
        # 스케줄 정보가 아예 없는 경우 제외
        if not course.courseschedule_set.exists():
            continue
        # course_schedule의 times가 "00"인 스케줄이 하나라도 있으면 제외
        skip = False
        for sch in course.courseschedule_set.all():
            if sch.times.strip() == "00":
                skip = True
                break
        if skip:
            continue
        # 공강요일 조건: 미리 추가되지 않은 강좌의 경우, 스케줄 중 하나라도 free_days에 있으면 후보에서 제외
        schedules = course.courseschedule_set.all()
        conflict_with_free_day = False
        for sch in schedules:
            if sch.day in free_days:
                conflict_with_free_day = True
                break
        if conflict_with_free_day:
            continue
        # 타입별 추가 조건:
        # 전공 강좌는 학생의 학과(dept)가 소프트웨어학부(dept_id=2)여야 함
        if course.course_type in ['전공필수', '전공선택']:
            if course.dept.dept_id != student_dept_id:
                continue
        # 교양 강좌는 year가 '전학년'이어야 함
        elif course.course_type == '교양선택':
            if course.year != '전학년':
                continue
        candidates.append(course)
    
    # 디버그 로그
    print("DEBUG: free_days =", free_days)
    print("DEBUG: pre_added_courses count =", len(pre_added_courses))
    print("DEBUG: candidates count =", len(candidates))
    print("DEBUG: Target 총학점 =", target_total, "전공학점 =", target_major, "교양학점 =", target_elective)
    
    # 4. 우선순위: 전공필수(3학년)을 우선 정렬
    def candidate_priority(course):
        return 0 if (course.course_type == '전공필수' and course.year == '3학년') else 1
    candidates_sorted = sorted(candidates, key=candidate_priority)
    
    # 5. 헬퍼 함수: 시간 슬롯, 시간 충돌 체크
    def get_time_slots(course):
        """
        주어진 강좌의 모든 스케줄을 분석하여, day별 시간 슬롯 집합을 반환.
        예) "03,04" → {11, 12} (8을 더함)
        """
        slots = {}
        for sch in course.courseschedule_set.all():
            day = sch.day
            try:
                time_slots = set(int(t.strip()) + 8 for t in sch.times.split(',') if t.strip().isdigit())
            except Exception:
                time_slots = set()
            if day in slots:
                slots[day].update(time_slots)
            else:
                slots[day] = time_slots
        return slots

    def courses_conflict(course1, course2):
        slots1 = get_time_slots(course1)
        slots2 = get_time_slots(course2)
        for day in slots1:
            if day in slots2 and slots1[day].intersection(slots2[day]):
                return True
        return False

    def has_conflict(selected_courses, new_course):
        for course in selected_courses:
            if courses_conflict(course, new_course):
                return True
        return False

    # 6. 백트래킹: 학점 제약 및 중복 과목명(같은 course_name) 제약 반영
    results = []         # 각 시간표는 강좌 객체들의 리스트
    max_results = 50
    start_time = time.time()
    max_time = 10        # 초

    # 초기 선택: 미리 추가한 강좌
    initial_selection = pre_added_courses.copy()
    # 초기 학점 합계 계산
    init_total = sum(course.credit for course in initial_selection)
    init_major = sum(course.credit for course in initial_selection if course.course_type in ['전공필수', '전공선택'])
    init_elective = sum(course.credit for course in initial_selection if course.course_type == '교양선택')
    # 초기 과목명 집합 (중복 방지를 위함)
    init_used_names = set(course.course_name for course in initial_selection)
    
    print("DEBUG: 초기 총학점 =", init_total, "전공학점 =", init_major, "교양학점 =", init_elective)
    
    def backtrack(index, current_selection, current_total, current_major, current_elective, used_names):
        nonlocal results
        # 시간 초과 체크
        if time.time() - start_time > max_time:
            return
        # 가지치기: 학점이 목표를 초과하면 중단
        if current_total > target_total or current_major > target_major or current_elective > target_elective:
            return
        # 학점이 정확히 일치하면 후보에 추가
        if current_total == target_total and current_major == target_major and current_elective == target_elective:
            results.append(current_selection.copy())
            print("DEBUG: 후보 시간표 추가, 현재 후보 수 =", len(results))
            if len(results) >= max_results:
                return
            # 계속 탐색할 수 있음 (다른 조합 찾기)
        # 후보 리스트에서 순회하며 추가
        for i in range(index, len(candidates_sorted)):
            candidate = candidates_sorted[i]
            # 같은 과목명 이미 포함된 경우 건너뜀 (중복 분반 방지)
            if candidate.course_name in used_names:
                continue
            # 시간 충돌 체크
            if has_conflict(current_selection, candidate):
                continue
            # 추가 후 학점 업데이트
            new_total = current_total + candidate.credit
            new_major = current_major + (candidate.credit if candidate.course_type in ['전공필수', '전공선택'] else 0)
            new_elective = current_elective + (candidate.credit if candidate.course_type == '교양선택' else 0)
            # 목표 초과면 건너뜀
            if new_total > target_total or new_major > target_major or new_elective > target_elective:
                continue
            # candidate 추가
            current_selection.append(candidate)
            used_names.add(candidate.course_name)
            backtrack(i + 1, current_selection, new_total, new_major, new_elective, used_names)
            if len(results) >= max_results:
                return
            # candidate 제거
            current_selection.pop()
            used_names.remove(candidate.course_name)
    
    backtrack(0, initial_selection, init_total, init_major, init_elective, init_used_names)
    
    print("DEBUG: 최종 생성된 시간표 후보 수 =", len(results))
    
    # 7. 결과 JSON 데이터 구성: 각 시간표 후보에 대해 강좌 정보를 course_id, course_name, section, credit, schedules 포함
    timetables_data = []
    for timetable in results:
        timetable_data = []
        for course in timetable:
            schedules = []
            for sch in course.courseschedule_set.all():
                schedules.append({
                    'day': sch.day,
                    'times': sch.times,
                    'location': sch.location
                })
            timetable_data.append({
                'course_id': course.course_id,
                'course_name': course.course_name,
                'section': course.section,
                'credit': course.credit,
                'schedules': schedules
            })
        timetables_data.append(timetable_data)
    
    def event_stream():
        result = {
            'progress': '완료',
            'found': len(timetables_data),
            'timetables': timetables_data
        }
        yield f"data: {json.dumps(result)}\n\n"
    
    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")


# 기존의 다른 뷰 함수들
def login_view(request):
    return render(request, "home/login.html")

def dashboard_view(request):
    return render(request, "home/dashboard.html")

def timetable_view(request):
    semester_id_filter = 21  # 25년도 1학기
    major_required = Course.objects.filter(semester_id=semester_id_filter, course_type='전공필수').order_by('course_name')
    major_elective = Course.objects.filter(semester_id=semester_id_filter, course_type='전공선택').order_by('course_name')
    general_elective = Course.objects.filter(semester_id=semester_id_filter, course_type='교양선택').order_by('course_name')
    free_elective = Course.objects.filter(semester_id=semester_id_filter, course_type='일반선택').order_by('course_name')
    teaching_required = Course.objects.filter(semester_id=semester_id_filter, course_type='교직필수').order_by('course_name')
    return render(request, "home/timetable.html", {
        'major_required': major_required,
        'major_elective': major_elective,
        'general_elective': general_elective,
        'free_elective': free_elective,
        'teaching_required': teaching_required,
    })
