import time
import json
import os
import logging
from collections import defaultdict

from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.conf import settings
from django.db.models.functions import Upper

from .models import Course, CourseSchedule, GraduationRecord, Department
from .services.pdf_service import pdf_to_text
from .services.gpt_service import extract_graduation_info_from_text
from .services.graduation_file_service import save_graduation_data_to_db

from ortools.sat.python import cp_model

# ------------------------------------
# 1. 효과적 교양 세부 항목 결정 함수
def get_effective_general_category(course):
    mapping = {
        "개신기초교양": "개신기초교양",
        "일반교양": "일반교양",
        "자연이공계기초": "자연이공계기초",
        "자연이공계기초과학": "자연이공계기초",  # 매핑
        "확대교양": "확대교양",
        "OCU": "OCU기타",
        "OCU 과목": "OCU기타",
    }
    if not hasattr(course, 'category') or not course.category:
        return ""
    cat = course.category
    if cat.category_name in mapping:
        return mapping[cat.category_name]
    if hasattr(cat, 'parent_category') and cat.parent_category:
        try:
            parent = cat.parent_category
            if parent.category_name in mapping:
                return mapping[parent.category_name]
        except Exception as e:
            print("ERROR: Parent category retrieval error for", cat.category_name, ":", e)
    return ""

# -----------------------------------------------------------------------------
# 2. generate_timetable_stream 함수
def generate_timetable_stream(request):
    """
    OR‑Tools CP‑SAT Solver를 사용하여 후보 시간표를 생성합니다.
    
    기존 조건 외에 아래 두 조건을 추가했습니다.
      - GraduationRecord.completed_courses는 강좌명(대문자) 기준으로 저장되므로, 이미 이수한 강좌를 후보에서 제외.
      - 교양강좌(교양선택)는 GraduationRecord.missing_general_sub(예, {"개신기초교양": 18, "자연이공계기초": 12, ...})
        에서 해당 세부 항목의 남은 학점이 0이면 후보에서 제외.
        
    단, 여기서는 CP‑SAT 모델을 구성한 후 단일 해(solution)를 구해 출력합니다.
    """
    start_time = time.time()
    print("DEBUG: --- Timetable Generation Start ---")
    
    # 2-1. GET 파라미터 파싱
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
    
    # 2-2. 미리 추가한 강좌 (반드시 포함)
    pre_added_courses = list(Course.objects.filter(course_id__in=pre_added_ids))
    print("DEBUG: pre_added_courses count =", len(pre_added_courses))
    
    # 2-3. 학생 정보 및 졸업 기록 로드
    student_id = request.user.id if request.user.is_authenticated else 1
    grad_record = GraduationRecord.objects.filter(user_id=student_id).last()
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
    
    dept_name = grad_record.user_major if grad_record and grad_record.user_major else ""
    dept_obj = Department.objects.filter(dept_name=dept_name).first()
    student_dept_id = dept_obj.dept_id if dept_obj else None
    print("DEBUG: student_dept_id =", student_dept_id)
    
    # 2-4. GraduationRecord에서 이수한 과목은 이제 강좌명(대문자) 기준
    completed_courses = []
    if grad_record and grad_record.completed_courses:
        try:
            completed_courses = json.loads(grad_record.completed_courses)
            completed_courses = [name.strip().upper() for name in completed_courses if name]
        except Exception as e:
            print("DEBUG: completed_courses parse error:", e)
            completed_courses = []
    print("DEBUG: completed_courses =", completed_courses)
    
    # 2-5. GraduationRecord의 missing_general_sub (교양 세부 이수 상태)
    missing_gen_sub = {}
    try:
        missing_gen_sub = json.loads(grad_record.missing_general_sub or '{}')
        missing_gen_sub = {k: int(v) for k, v in missing_gen_sub.items()}
    except Exception as e:
        print("DEBUG: missing_gen_sub parse error:", e)
        missing_gen_sub = {}
    print("DEBUG: missing_gen_sub =", missing_gen_sub)
    
    # 3. 후보 강좌 조회 (필터링)
    # completed_courses는 강좌명(대문자) 기준으로 비교하므로, Course의 course_name을 대문자로 변환
    candidate_qs = Course.objects.filter(
        semester_id=21,
        course_type__in=['전공필수', '전공선택', '교양선택']
    ).annotate(upper_course_name=Upper('course_name')).exclude(upper_course_name__in=[name.upper() for name in completed_courses])
    
    candidates = []
    for course in candidate_qs:
        # 전공 강좌: 학생의 현재 학년보다 높은 강좌 제외
        if course.course_type in ['전공필수', '전공선택']:
            if course.year != "전학년":
                try:
                    course_year = int(course.year[0])
                except Exception:
                    course_year = 0
                if course_year > current_year:
                    continue
            if student_dept_id is not None and course.dept.dept_id != student_dept_id:
                continue
        # 기존 필터: 미리 추가된 강좌, 학점 0, 스케줄 정보 없음, times가 "00"인 강좌 제외
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
        # 추가 필터: 교양 강좌의 경우, 이미 해당 세부 교양 영역의 남은 학점이 0이면 제외
        if course.course_type == '교양선택':
            effective_cat = get_effective_general_category(course)
            if effective_cat and missing_gen_sub.get(effective_cat, 0) == 0:
                print("DEBUG: Excluding 교양 course", course.course_name, "as", effective_cat, "is already completed.")
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
        cand_dict = {
            'id': course.course_id,
            'credit': course.credit,
            'course_type': course.course_type,
            'course_name': course.course_name,
            'year': course.year,
            'schedule': schedule_list,
            'location': locations[0] if locations else "",
            'pre_added': course.course_id in pre_added_ids
        }
        if course.course_type == '교양선택':
            cand_dict['effective_category'] = get_effective_general_category(course)
        candidate_data.append(cand_dict)
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
    
    # 시간 충돌 제약
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
    
    # 동일 과목명 중복 제약
    name_groups = defaultdict(list)
    for data in candidate_data:
        name_groups[data['course_name']].append(data['id'])
    for name, ids in name_groups.items():
        model.Add(sum(x[cid] for cid in ids) <= 1)
    
    # 6. (옵션) 객관식 최적화—여기서는 전공(전공필수+전공선택)을 우선하도록 하기 위해 최적화 함수 사용
    # 단, 본질적으로는 제약 조건을 만족하는 해가 존재하면 그 해를 출력하도록 합니다.
    required_priority = sum(x[data['id']] for data in candidate_data 
                            if data['course_type'] == '전공필수' and (data['year'] == "전학년" or int(data.get('year', '0')[0]) <= current_year))
    elective_priority = 0.1 * sum(x[data['id']] for data in candidate_data 
                                    if data['course_type'] == '전공선택' and (data['year'] == "전학년" or int(data.get('year', '0')[0]) == current_year))
    model.Maximize(required_priority + elective_priority)
    
    solver = cp_model.CpSolver()
    print("DEBUG: Starting CP-SAT solve...")
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return JsonResponse({"error": "해결책을 찾지 못했습니다."}, status=500)
    
    # 7. 해(solution) 추출 (기존 코드 방식)
    solution = []
    for data in candidate_data:
        if solver.Value(x[data['id']]) == 1:
            solution.append(data)
    
    # 출력 순서를 전공 강좌가 먼저 나오도록 정렬 (전공필수와 전공선택 -> 교양)
    def sort_key(item):
        if item['course_type'] in ['전공필수', '전공선택']:
            return (0, item['course_name'])
        else:
            return (1, item['course_name'])
    solution.sort(key=sort_key)
    
    print("DEBUG: Final solution ({} courses):".format(len(solution)))
    for item in solution:
        print("DEBUG:", item['course_name'], item['course_type'], item['credit'], "점")
    
    total_time = time.time() - start_time
    print("DEBUG: --- Timetable Generation End --- (Elapsed: {:.2f} seconds)".format(total_time))
    
    result = {
        'progress': '완료',
        'found': 1,
        'timetables': [solution],
        'message': f"총 1개의 시간표를 찾았습니다."
    }
    def event_stream():
        yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"
    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

# ---------------------------
# 나머지 뷰 함수들
def login_view(request):
    return render(request, "home/login.html")

def dashboard_view(request):
    return render(request, "home/dashboard.html")

def mypage_view(request):
    import json
    user_id = request.user.id if request.user.is_authenticated else 1
    record = GraduationRecord.objects.filter(user_id=user_id).last()
    context = {}
    if record:
        context['user_student_id'] = getattr(record, 'user_student_id', "")
        context['user_name'] = getattr(record, 'user_name', "")
        context['user_major'] = getattr(record, 'user_major', "")
        context['user_year'] = getattr(record, 'user_year', "")
        context['total_credits'] = getattr(record, 'total_credits', 0)
        context['major_credits'] = getattr(record, 'major_credits', 0)
        context['general_credits'] = getattr(record, 'general_credits', 0)
        context['free_credits'] = getattr(record, 'free_credits', 0)
        context['total_requirement'] = getattr(record, 'total_requirement', 0)
        context['major_requirement'] = getattr(record, 'major_requirement', 0)
        context['general_requirement'] = getattr(record, 'general_requirement', 0)
        context['free_requirement'] = getattr(record, 'free_requirement', 0)
        try:
            context['major_requirement_data'] = json.loads(record.major_requirement or '{}')
        except:
            context['major_requirement_data'] = {}
        try:
            context['general_requirement'] = json.loads(record.general_requirement or '{}')
        except:
            context['general_requirement'] = {}
        try:
            context['detailed_credits'] = json.loads(record.detailed_credits or '{}')
        except:
            context['detailed_credits'] = {}
        try:
            missing_subjects = json.loads(record.missing_major_subjects or '[]')
            context['missing_subjects'] = missing_subjects if isinstance(missing_subjects, list) else []
        except:
            context['missing_subjects'] = []
        try:
            completed_courses = json.loads(record.completed_courses or '[]')
            context['completed_courses'] = completed_courses if isinstance(completed_courses, list) else []
        except:
            context['completed_courses'] = []
        try:
            missing_general_sub_raw = json.loads(record.missing_general_sub or '{}')
            context['missing_general_sub'] = missing_general_sub_raw if isinstance(missing_general_sub_raw, dict) else {}
        except:
            context['missing_general_sub'] = {}
        context['missing_total'] = max(0, context['total_requirement'] - context['total_credits'])
    else:
        context.update({
            'user_student_id': "", 'user_name': "", 'user_major': "", 'user_year': "",
            'total_credits': 0, 'major_credits': 0, 'general_credits': 0, 'free_credits': 0,
            'total_requirement': 0, 'major_requirement_data': {}, 'free_requirement': 0,
            'missing_total': 0, 'missing_major': 0, 'missing_major_essential': 0,
            'missing_major_elective': 0, 'missing_general': 0, 'missing_free': 0,
            'missing_subjects': [], 'completed_courses': [], 'missing_general_sub': {},
            'detailed_credits': {}, 'general_requirement': {},
            'error_message': "졸업 정보를 찾을 수 없습니다. 성적표 PDF를 업로드해주세요."
        })
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


def course_serach_test_view(request):
    return render(request, 'home/search_test.html')
