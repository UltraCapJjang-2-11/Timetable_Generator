import time
import json
from django.http import StreamingHttpResponse, JsonResponse
import os
from django.shortcuts import render, redirect
from django.db import models
from django.conf import settings
from .models import Course, CourseSchedule, Department
from collections import defaultdict

from .services.pdf_service import pdf_to_text
from .services.gpt_service import extract_graduation_info_from_text
from .services.graduation_file_service import save_graduation_data_to_db

# OR‑Tools CP‑SAT Solver import (pip install ortools)
from ortools.sat.python import cp_model

import time
import json
import os
from collections import defaultdict

from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.conf import settings
from django.db.models.functions import Upper

from .models import Course, CourseSchedule, GraduationRecord
from .services.pdf_service import pdf_to_text
from .services.gpt_service import extract_graduation_info_from_text
from .services.graduation_file_service import save_graduation_data_to_db

# OR‑Tools CP‑SAT Solver (pip install ortools)
from ortools.sat.python import cp_model

def generate_timetable_stream(request):
    """
    OR‑Tools CP‑SAT Solver를 사용하여 후보 시간표를 생성합니다.
    
    조건:
      1. 총학점, 전공학점, 교양학점이 사용자가 입력한 값과 정확히 일치
      2. 같은 요일, 같은 시간 슬롯에는 한 강좌만 배치 (시간 충돌 방지)
      3. 같은 과목명 중복 배제
      4. 0학점 강좌, 스케줄 정보 없음, times=="00"인 강좌는 후보에서 제외
      5. 미리 추가한 강좌는 반드시 선택
      6. 학생의 현재 학년보다 높은 전공 강좌는 후보에서 제외
         - 전공필수는 동일학년 또는 아래학년 강좌를 (충돌이 없으면) 반드시 포함
         - 전공선택은 같은 학년의 강좌를 우선하도록 함
      7. 이수한 과목(과목코드)는 GraduationRecord에 저장된 목록을 읽어 후보에서 제외
      8. GraduationRecord의 user_major(학과)를 사용하여 Department 테이블에서 dept_id를 조회한 후,
         전공 강좌의 경우 해당 dept_id와 일치하는 강좌만 후보에 포함
    최종 후보(최대 50개)를 JSON 형식의 SSE 메시지로 전송합니다.
    """
    # 1. GET 파라미터 파싱
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
        return JsonResponse({"error": "학점 파라미터가 올바르지 않습니다."}, status=500)
    
    print("DEBUG: free_days =", free_days)
    print("DEBUG: pre_added_ids =", pre_added_ids)
    print("DEBUG: target_total =", target_total, "target_major =", target_major, "target_elective =", target_elective)
    
    # 2. 미리 추가한 강좌 (반드시 포함)
    pre_added_courses = list(Course.objects.filter(course_id__in=pre_added_ids))
    print("DEBUG: pre_added_courses count =", len(pre_added_courses))
    
    # 학생 ID 및 GraduationRecord에서 현재 학년과 학과(전공) 정보 설정
    student_id = request.user.id if request.user.is_authenticated else 1
    grad_record = GraduationRecord.objects.filter(user_id=student_id).last()
    
    # 현재 학년: "전학년"이면 매우 큰 값으로 처리하여 모든 강좌 포함, 아니면 첫 글자를 정수로 파싱
    try:
        if grad_record and grad_record.user_year:
            if grad_record.user_year == "전학년":
                current_year = 100
            else:
                current_year = int(grad_record.user_year[0])
        else:
            current_year = 3
    except Exception:
        current_year = 3
    print("DEBUG: current_year =", current_year)
    
    # GraduationRecord에 저장된 user_major(학과)를 사용하여 Department 테이블에서 dept_id 조회
    dept_name = grad_record.user_major if grad_record and grad_record.user_major else ""
    dept_obj = Department.objects.filter(dept_name=dept_name).first()
    student_dept_id = dept_obj.dept_id if dept_obj else None
    print("DEBUG: student_dept_id =", student_dept_id)
    
    # 2-1. GraduationRecord에서 이수한 과목(과목코드) 불러오기
    completed_courses = []
    if grad_record and grad_record.completed_courses:
        try:
            completed_courses = json.loads(grad_record.completed_courses)
            completed_courses = [code.strip().upper() for code in completed_courses if code]
        except Exception as e:
            print("DEBUG: completed_courses parse error:", e)
            completed_courses = []
    print("DEBUG: completed_courses =", completed_courses)
    
    # 3. 후보 강좌 조회 (필터링)
    # Course의 course_code를 대문자로 변환하여 비교
    candidate_qs = Course.objects.filter(
        semester_id=21,
        course_type__in=['전공필수', '전공선택', '교양선택']
    ).annotate(upper_course_code=Upper('course_code')).exclude(upper_course_code__in=completed_courses)
    
    candidates = []
    for course in candidate_qs:
        # 전공 강좌: 학생의 현재 학년보다 높은 강좌는 제외 (단, "전학년"이면 모두 포함)
        if course.course_type in ['전공필수', '전공선택']:
            if course.year != "전학년":
                try:
                    course_year = int(course.year[0])
                except Exception:
                    course_year = 0
                if course_year > current_year:
                    continue
            # 학과 조건: GraduationRecord에서 조회한 student_dept_id와 일치해야 함
            if student_dept_id is not None and course.dept.dept_id != student_dept_id:
                continue
        # 기존 필터: 미리 추가된 강좌, 학점 0, 스케줄 정보 없음, times=="00"인 강좌 제외
        if course.course_id in pre_added_ids:
            continue
        if course.credit <= 0:
            continue
        if not course.courseschedule_set.exists():
            continue
        skip = False
        for sch in course.courseschedule_set.all():
            if sch.times.strip() == "00":
                skip = True
                break
        if skip:
            continue
        conflict_with_free_day = False
        for sch in course.courseschedule_set.all():
            if sch.day in free_days:
                conflict_with_free_day = True
                break
        if conflict_with_free_day:
            continue
        # 교양 강좌는 반드시 '전학년'이어야 함
        if course.course_type == '교양선택' and course.year != '전학년':
            continue
        candidates.append(course)
    print("DEBUG: candidates count =", len(candidates))
    all_candidates = pre_added_courses + candidates
    print("DEBUG: all_candidates count =", len(all_candidates))
    
    # 4. 전처리: 각 후보 강좌의 스케줄 정보를 candidate_data에 저장
    candidate_data = []
    for course in all_candidates:
        schedule_list = []
        locations = []
        for sch in course.courseschedule_set.all():
            raw = sch.times.strip()
            if "@" in raw:
                parts = raw.split("@")
                raw_time = parts[0]
                loc = parts[1]
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
            locations.append(sch.location)
        if not schedule_list:
            continue
        candidate_data.append({
            'id': course.course_id,
            'credit': course.credit,
            'course_type': course.course_type,
            'course_name': course.course_name,
            'year': course.year,  # 예: "3학년", "전학년" 등
            'schedule': schedule_list,
            'location': locations[0] if locations else "",
            'pre_added': course.course_id in pre_added_ids
        })
    print("DEBUG: candidate_data count =", len(candidate_data))
    
    # 5. CP‑SAT 모델 구성
    model = cp_model.CpModel()
    x = {}
    for data in candidate_data:
        x[data['id']] = model.NewBoolVar(f"course_{data['id']}")
    
    # 미리 추가한 강좌는 강제 선택
    for data in candidate_data:
        if data.get('pre_added', False):
            model.Add(x[data['id']] == 1)
    
    model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data) == target_total)
    model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data if data['course_type'] in ['전공필수', '전공선택']) == target_major)
    model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data if data['course_type'] == '교양선택') == target_elective)
    
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
    
    name_groups = defaultdict(list)
    for data in candidate_data:
        name_groups[data['course_name']].append(data['id'])
    for name, ids in name_groups.items():
        model.Add(sum(x[cid] for cid in ids) <= 1)
    
    # 6. 목표 함수 설정
    # 전공필수: 학생의 현재 학년 이하(또는 '전학년')의 강좌를 최대한 포함하도록 우선 부여
    required_priority = sum(x[data['id']] for data in candidate_data 
                            if data['course_type'] == '전공필수' and (data['year'] == "전학년" or int(data.get('year', '0')[0]) <= current_year))
    # 전공선택: 같은 학년 강좌에 낮은 우선순위 부여 (가중치 0.1)
    elective_priority = 0.1 * sum(x[data['id']] for data in candidate_data 
                                    if data['course_type'] == '전공선택' and (data['year'] == "전학년" or int(data.get('year', '0')[0]) == current_year))
    model.Maximize(required_priority + elective_priority)
    
    solver = cp_model.CpSolver()
    print("DEBUG: Starting Phase 1 optimization...")
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return JsonResponse({"error": "해결책을 찾지 못했습니다."}, status=500)
    best_value = solver.ObjectiveValue()
    print("DEBUG: Phase 1 Best objective =", best_value)
    
    # 7. Phase 2: 새 모델 구성 (최적 목표값 강제)
    model2 = cp_model.CpModel()
    x2 = {}
    for data in candidate_data:
        x2[data['id']] = model2.NewBoolVar(f"course2_{data['id']}")
    
    for data in candidate_data:
        if data.get('pre_added', False):
            model2.Add(x2[data['id']] == 1)
    
    model2.Add(sum(data['credit'] * x2[data['id']] for data in candidate_data) == target_total)
    model2.Add(sum(data['credit'] * x2[data['id']] for data in candidate_data if data['course_type'] in ['전공필수', '전공선택']) == target_major)
    model2.Add(sum(data['credit'] * x2[data['id']] for data in candidate_data if data['course_type'] == '교양선택') == target_elective)
    
    for (day, slot), ids in slot_mapping.items():
        model2.Add(sum(x2[cid] for cid in ids) <= 1)
    
    for name, ids in name_groups.items():
        model2.Add(sum(x2[cid] for cid in ids) <= 1)
    
    # 동일 학년 이하(또는 '전학년')의 전공필수 강좌 선택 수를 Phase 1 목표값(best_value)와 동일하게 강제
    model2.Add(sum(x2[data['id']] for data in candidate_data 
               if data['course_type'] == '전공필수' and (data['year'] == "전학년" or int(data.get('year', '0')[0]) <= current_year)) == int(best_value))
    
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
                        'course_name': data['course_name'],
                        'credit': data['credit'],
                        'course_type': data['course_type'],
                        'schedules': data['schedule'],
                        'location': data['location']
                    })
            self._solutions.append(solution)

        def Solutions(self):
            return self._solutions

    solution_collector2 = TimetableSolutionCollector(x2, candidate_data, limit=500000)
    solver2 = cp_model.CpSolver()
    print("DEBUG: Starting Phase 2 search for all solutions...")
    solver2.SearchForAllSolutions(model2, solution_collector2)
    print("DEBUG: Phase 2 search finished. Total solutions:", solution_collector2._solution_count)
    
    timetables_data = solution_collector2.Solutions()
    result = {
        'progress': '완료',
        'found': len(timetables_data),
        'timetables': timetables_data
    }
    def event_stream():
        yield f"data: {json.dumps(result)}\n\n"
    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

def login_view(request):
    return render(request, "home/login.html")

def dashboard_view(request):
    return render(request, "home/dashboard.html")

def manage_view(request):
    return render(request, "home/manage.html")    

def mypage_view(request):
    from .models import GraduationRecord
    import json
    user_id = request.user.id if request.user.is_authenticated else 1

    record = GraduationRecord.objects.filter(user_id=user_id).last()

    if record:
        total_credits = record.total_credits
        major_credits = record.major_credits
        general_credits = record.general_credits
        free_credits = record.free_credits
        user_student_id = record.user_student_id or ""
        user_name = record.user_name or ""
        user_major = record.user_major or ""
        user_year = record.user_year or ""
        total_requirement = record.total_requirement or 0
        major_requirement = record.major_requirement or 0
        general_requirement = record.general_requirement or 0
        free_requirement = record.free_requirement or 0

        try:
            raw_alerts = json.loads(record.missing_major_subjects)
            alerts = []
            for item in raw_alerts:
                alert_str = f"{item.get('type', '')}: {item.get('description', '')}"
                alerts.append(alert_str)
        except Exception:
            alerts = []
    else:
        total_credits = major_credits = general_credits = free_credits = 0
        user_student_id = user_name = user_major = user_year = ""
        total_requirement = major_requirement = general_requirement = free_requirement = 0
        alerts = []

    missing_total = total_requirement - total_credits
    missing_major = major_requirement - major_credits
    missing_general = general_requirement - general_credits
    missing_free = free_requirement - free_credits

    context = {
        'user_student_id': user_student_id,
        'user_name': user_name,
        'user_major': user_major,
        'user_year': user_year,  # 학년 정보
        'alerts': alerts,  # 포맷팅된 미이수 과목 알림
        'total_credits': total_credits,
        'major_credits': major_credits,
        'general_credits': general_credits,
        'free_credits': free_credits,
        'total_requirement': total_requirement,
        'major_requirement': major_requirement,
        'general_requirement': general_requirement,
        'free_requirement': free_requirement,
        'missing_total': missing_total,
        'missing_major': missing_major,
        'missing_general': missing_general,
        'missing_free': missing_free,
    }
    return render(request, 'home/mypage.html', context)




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

def upload_pdf_view(request):
    """
    1) PDF 업로드 받음
    2) 임시 저장
    3) pdfplumber로 텍스트 추출
    4) GPT API로 분석 (JSON)
    5) DB 저장 후 mypage로 리디렉션
    """
    if request.method == "POST":
        pdf_file = request.FILES.get("graduation_pdf")
        if not pdf_file:
            return JsonResponse({"error": "파일이 업로드되지 않았습니다."}, status=400)

        file_path = os.path.join(settings.BASE_DIR, "user_uploads", pdf_file.name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb+") as dest:
            for chunk in pdf_file.chunks():
                dest.write(chunk)

        text = pdf_to_text(file_path)
        print("debug text:", text)
        parsed_data = extract_graduation_info_from_text(text)
        user_id = request.user.id if request.user.is_authenticated else 1
        record = save_graduation_data_to_db(parsed_data, user_id)

        return redirect('mypage')
    else:
        return render(request, "home/upload_pdf.html")
