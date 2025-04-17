import time
import json
import os
import logging
from collections import defaultdict

from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.conf import settings
from django.db.models import Q
from django.db.models.functions import Upper

from .models import Course, CourseSchedule, GraduationRecord, Department
from .services.pdf_service import pdf_to_text
from .services.gpt_service import extract_graduation_info_from_text
from .services.graduation_file_service import save_graduation_data_to_db

from ortools.sat.python import cp_model

# ------------------------------------
# 1. 효과적 교양 세부 항목 결정 함수 (기존과 동일)
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

# ------------------------------------
# 2. 미이수 전공필수 과목 추출 함수 (변경 없음)
def extract_missing_required_major_courses(user_dept_id, completed_courses):
    """
    사용자 전공(dept_id)에 해당하는 전공필수 강좌 중,
    이미 이수한 과목(completed_courses 집합)에 포함되지 않은 고유 course_name(대문자 기준)들을 반환.
    """
    missing_courses = set()
    required_courses = Course.objects.filter(category__category_name='전공필수', dept__dept_id=user_dept_id)
    for course in required_courses:
        cname = course.course_name.strip().upper()
        if cname not in completed_courses:
            missing_courses.add(cname)
    return missing_courses

# ------------------------------------
# 3. generate_timetable_stream 함수 (교양의 parent_category 조건 추가)
def generate_timetable_stream(request):
    """
    기존 코드에서 아래 조건들을 처리합니다.
      - GraduationRecord.completed_courses 필드는 강좌명(대문자)으로 저장되므로 이를 기준으로 후보에서 이미 이수한 강좌를 제외.
      - 교양 강좌의 경우, get_effective_general_category()를 이용하여 해당 강좌의 세부 항목을 구하고,
        GraduationRecord.missing_general_sub (예, {"개신기초교양": 15, "자연이공계기초": 12, ...})에서 해당 항목의 값이 0이면 후보에서 제외.
      - 전공선택 과목은 동일학년 여부를 체크하여, 필요 시 낮은 학년 강좌는 후보에서 제외합니다.
    """
    start_time = time.time()
    print("DEBUG: --- Timetable Generation Start ---")
    
    # 3-1. GET 파라미터 파싱
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
    
    # 3-2. 미리 추가한 강좌 (반드시 포함)
    pre_added_courses = list(Course.objects.filter(course_id__in=pre_added_ids))
    print("DEBUG: pre_added_courses count =", len(pre_added_courses))
    
    # 3-3. 학생 정보 및 졸업 기록 로드
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
    
    # 3-4. completed_courses는 강좌명이므로, Course의 course_name(대문자) 기준으로 비교합니다.
    completed_courses = []
    if grad_record and grad_record.completed_courses:
        try:
            completed_courses = json.loads(grad_record.completed_courses)
            completed_courses = [name.strip().upper() for name in completed_courses if name]
        except Exception as e:
            print("DEBUG: completed_courses parse error:", e)
            completed_courses = []
    print("DEBUG: completed_courses =", completed_courses)
    
    # 3-5. graduation_record의 missing_general_sub (교양 세부 이수 상태)
    missing_gen_sub = {}
    try:
        missing_gen_sub = json.loads(grad_record.missing_general_sub or '{}')
        missing_gen_sub = {k: int(v) for k, v in missing_gen_sub.items()}
    except Exception as e:
        print("DEBUG: missing_general_sub parse error:", e)
        missing_gen_sub = {}
    print("DEBUG: missing_gen_sub =", missing_gen_sub)
    
    # 3-6. 후보 강좌 조회 (필터링)
    general_categories = ["개신기초교양", "일반교양", "자연이공계기초", "자연이공계기초과학", "확대교양", "OCU", "OCU 과목"]
    candidate_qs = Course.objects.filter(
        semester_id=21
    ).filter(
        Q(category__category_name__in=['전공필수', '전공선택']) |
        Q(category__category_name__in=general_categories) |
        Q(category__parent_category__category_name__in=general_categories)
    ).annotate(upper_course_name=Upper('course_name')).exclude(
        upper_course_name__in=[name.upper() for name in completed_courses]
    )
    
    candidates = []
    for course in candidate_qs:
        # 전공 강좌: 현재 학년보다 높은 강좌는 제외 및 전공 소속 학과 여부 체크
        if course.category.category_name in ['전공필수', '전공선택']:
            print("DEBUG: Checking course", course.course_name)
            if course.year != "전학년":
                try:
                    course_year = int(course.year[0])
                except Exception:
                    course_year = 0
                if course_year > current_year:
                    continue
            if student_dept_id is not None and course.dept.dept_id != student_dept_id:
                continue
        # 기본 필터
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
        # 교양 강좌: 반드시 '전학년'이어야 함
        if get_effective_general_category(course) and course.year != '전학년':
            continue
        # 추가 필터: 교양 강좌(구 교양선택)의 경우, 해당 세부 항목의 남은 학점이 0이면 후보에서 제외
        if get_effective_general_category(course):
            effective_cat = get_effective_general_category(course)
            if missing_gen_sub.get(effective_cat, 0) == 0:
                print("DEBUG: Excluding 교양 course", course.course_name, "as", effective_cat, "is already completed.")
                continue
        candidates.append(course)
    print("DEBUG: candidates count =", len(candidates))
    all_candidates = pre_added_courses + candidates
    print("DEBUG: all_candidates count =", len(all_candidates))
    
    # 3-7. 전처리: 각 후보 강좌의 스케줄 정보를 candidate_data에 저장
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
            'credit': course.credit,
            'category': course.category.category_name,  # course_type
            'course_name': course.course_name,
            'year': course.year,
            'schedule': schedule_list,
            'location': locations[0] if locations else "",
            'pre_added': course.course_id in pre_added_ids
        }
        # 교양 강좌: effective_category 추가
        if get_effective_general_category(course):
            data_item['effective_category'] = get_effective_general_category(course)
        candidate_data.append(data_item)
    print("DEBUG: candidate_data count =", len(candidate_data))
    
    # ===== 수정된 부분: 전공선택 강좌 중 동일학년 강좌 우선 필터링 =====
    for data in candidate_data:
        if data['category'] == '전공선택':
            if data['year'] == "전학년" or (data['year'] and data['year'][0].isdigit() and int(data['year'][0]) == current_year):
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
        else:
            print("DEBUG: 동일학년 전공선택 강좌가 부족하여 낮은학년 전공선택 과목을 허용합니다.")
    # ===== 수정된 부분 끝 =====
    
    # 4. CP‑SAT 모델 구성 (후속 부분은 기존과 동일)
    model = cp_model.CpModel()
    x = {}
    for data in candidate_data:
        x[data['id']] = model.NewBoolVar(f"course_{data['id']}")
    
    for data in candidate_data:
        if data.get('pre_added', False):
            model.Add(x[data['id']] == 1)
    
    model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data) == target_total)
    model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data if data['category'] in ['전공필수', '전공선택']) == target_major)
    model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data if get_effective_general_category(course=DummyObj({'effective':data.get('effective_category', None)})) or data['category'] not in ['전공필수','전공선택']) == target_elective)
    
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
    
    name_groups = defaultdict(list)
    for data in candidate_data:
        name_groups[data['course_name']].append(data['id'])
    for name, ids in name_groups.items():
        model.Add(sum(x[cid] for cid in ids) <= 1)
    
    required_priority = sum(
        x[data['id']] for data in candidate_data 
        if data['category'] == '전공필수' and (data['year'] == "전학년" or (data['year'][0].isdigit() and int(data['year'][0]) <= current_year))
    )
    elective_priority = 0.1 * sum(
        x[data['id']] for data in candidate_data 
        if data['category'] == '전공선택' and (data['year'] == "전학년" or (data['year'][0].isdigit() and int(data['year'][0]) == current_year))
    )
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
    model2.Add(sum(data['credit'] * x2[data['id']] for data in candidate_data if data['category'] in ['전공필수', '전공선택']) == target_major)
    model2.Add(sum(data['credit'] * x2[data['id']] for data in candidate_data if get_effective_general_category(course=DummyObj({'effective':data.get('effective_category', None)})) or data['category'] not in ['전공필수','전공선택']) == target_elective)
    
    for (day, slot), ids in slot_mapping.items():
        model2.Add(sum(x2[cid] for cid in ids) <= 1)
    for name, ids in name_groups.items():
        model2.Add(sum(x2[cid] for cid in ids) <= 1)
    model2.Add(sum(x2[data['id']] for data in candidate_data 
               if data['category'] == '전공필수' and (data['year'] == "전학년" or (data['year'][0].isdigit() and int(data['year'][0]) <= current_year))) == int(best_value))
    print("DEBUG: Phase 2 credit constraints added; forcing Phase 1 optimal objective =", best_value)
    
    # CP‑SAT 해 solution 수집 방식 (Collector)
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
                        'category': data['category'],
                        'schedules': data['schedule'],
                        'location': data['location']
                    })
            self._solutions.append(solution)

        def Solutions(self):
            return self._solutions

    collector2 = TimetableSolutionCollector(x2, candidate_data, limit=50)
    solver2 = cp_model.CpSolver()
    print("DEBUG: Starting Phase 2 search for all solutions...")
    solver2.SearchForAllSolutions(model2, collector2)
    print("DEBUG: Phase 2 search finished. Total solutions:", collector2._solution_count)
    
    timetables_data = collector2.Solutions()
    print("DEBUG: Total unique solutions found:", len(timetables_data))
    print("DEBUG: --- Timetable Generation End ---")
    
    result = {
        'progress': '완료',
        'found': len(timetables_data),
        'timetables': timetables_data,
        'message': f"총 {len(timetables_data)}개의 시간표를 찾았습니다." if timetables_data else "조건에 맞는 시간표를 찾지 못했습니다. 조건을 변경해보세요."
    }
    def event_stream():
        yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"
    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

# ---------------------------
# 나머지 뷰 함수들 (변경 없음)
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
    major_required = Course.objects.filter(semester_id=semester_id_filter, category__category_name='전공필수').order_by('course_name')
    major_elective = Course.objects.filter(semester_id=semester_id_filter, category__category_name='전공선택').order_by('course_name')
    general_elective = Course.objects.filter(semester_id=semester_id_filter).filter(
        Q(category__category_name__in=["개신기초교양", "일반교양", "자연이공계기초", "자연이공계기초과학", "확대교양", "OCU", "OCU 과목"]) |
        Q(category__parent_category__category_name__in=["개신기초교양", "일반교양", "자연이공계기초", "자연이공계기초과학", "확대교양", "OCU", "OCU 과목"])
    ).order_by('course_name')
    free_elective = Course.objects.filter(semester_id=semester_id_filter, category__category_name='일반선택').order_by('course_name')
    teaching_required = Course.objects.filter(semester_id=semester_id_filter, category__category_name='교직').order_by('course_name')
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

# Helper Dummy class for elective CP‑SAT 조건 처리 (필요에 따라 별도 처리)
class DummyObj:
    def __init__(self, data):
        self.__dict__.update(data)
