import os
import traceback
from collections import defaultdict

from django.contrib.auth import logout
from django.db.models.functions import Upper
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render, redirect
from django.conf import settings
from data_manager.course.course_filter_service import CourseFilterService
from data_manager.models import *
from .forms import CustomUserCreationForm
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
import random
from .models import Course 
from .services.gpt_service import extract_graduation_info_from_text
from .services.graduation_file_service import save_graduation_data_to_db
from .services.pdf_service import pdf_to_text
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
import json

from ortools.sat.python import cp_model

import openai
# views.py 
@csrf_exempt
def parse_constraints(request):
    data = json.loads(request.body)
    user_text = data.get("text", "")

    system_prompt = """
    당신은 시간표 생성용 제약조건을 파싱하는 어시스턴트입니다.
    입력된 한국어 자연어에서 아래 키를 가진 JSON만 출력하세요.

    • major_credits: 전공 학점 (정수)
    • elective_credits: 교양 학점 (정수)
    • required_courses: 필수 포함 과목명 리스트 (문자열 리스트)
    • free_days: 공강 요일 리스트 (예: ["월","화",...])
    • avoid_times: 특정 요일·단일 시각 회피 리스트
        – 예: "월요일 9시 수업 제외" → {"day":"월","hour":9}
        "월,목 9시를 공강으로 시간표를 생성해줘"라고 하면 월요일 9시와 목요일 9시만을 공강으로 정해야해. 
        월,목을 공강으로 인식하면 안 돼. 제대로해.
    • avoid_time_ranges: 특정 요일·시간대 범위 회피 리스트
        – “금요일 오전 수업 제외” → {"days":["금"],"start_hour":9,"end_hour":12}
        – “오후 1시부터 4시 제외” → {"days":["월","화","수","목","금"],"start_hour":13,"end_hour":16}
    • only_time_ranges: 허용할 시간대 리스트 (이 외 시간대는 모두 제외)
        – 예: "월·수·목 11시 이후만" → {"days":["월","수","목"],"start_hour":11}
    • exclude_courses: 기존에 생성된 시간표에서 제외할 과목명 리스트
    — 키 외에는 절대 다른 텍스트를 포함하지 마세요.
    """

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system", "content": system_prompt},
                {"role":"user",   "content": user_text}
            ],
            temperature=0.0,
        )
        parsed = json.loads(resp.choices[0].message.content)
        return JsonResponse(parsed)
    except Exception as e:
        return JsonResponse({"error": f"파싱 실패: {e}"}, status=500)

    
class CustomLoginView(LoginView):
    template_name = 'home/login.html'
    authentication_form = AuthenticationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 회원가입 폼이 없으면 추가
        if 'register_form' not in context:
            context['register_form'] = CustomUserCreationForm()
        return context

def signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "회원가입이 완료되었습니다. 로그인 해주세요.")
            return redirect('login')
        else:
            messages.error(request, "회원가입 정보를 확인해주세요.")
    else:
        form = CustomUserCreationForm()

    login_form = AuthenticationForm()
    return render(request, 'home/login.html', {
        'signup_form': form,
        'login_form': login_form
    })

def logout_view(request):
    logout(request)
    return redirect('login')

def index_view(request):
    # 로그인 여부를 판단하고, 로그인 페이지 혹은 대쉬보드 페이지로 이동
    if request.user.is_authenticated:
        return render(request, 'home/dashboard.html')
    else:
        return redirect('/login')

def course_serach_test_view(request):
    return render(request, 'home/search_test.html')

def timetable_view(request):

    service = CourseFilterService()

    # 25년도 1학기
    year = 2025
    term = "1학기"

    major_required = service.course_search(year = year, term = term, category_name='전공필수').order_by('course_name')
    major_elective = service.course_search(year = year, term = term, category_name='전공선택').order_by('course_name')
    general_elective = service.course_search(year = year, term = term, category_name='교양').order_by('course_name')
    free_elective = service.course_search(year = year, term = term, category_name='일선').order_by('course_name')
    teaching_required = service.course_search(year = year, term = term, category_name='교직').order_by('course_name')

    return render(request, "home/timetable.html", {
        'major_required': major_required,
        'major_elective': major_elective,
        'general_elective': general_elective,
        'free_elective': free_elective,
        'teaching_required': teaching_required,
    })

def dashboard_view(request):
    return render(request, 'home/dashboard.html')

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
        # print("debug text:", text)
        parsed_data = extract_graduation_info_from_text(text)
        user_id = request.user.id if request.user.is_authenticated else 1
        record = save_graduation_data_to_db(parsed_data, user_id)
        return redirect('mypage')

def mypage_view(request):
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


# Helper Dummy class for elective CP‑SAT 조건 처리 (필요에 따라 별도 처리)
class DummyObj:
    def __init__(self, data):
        self.__dict__.update(data)

def get_effective_general_category(course) -> str:
    """
    Courses.category (FK)로부터 Category 트리를 타고 올라가
    '개신기초교양', '일반교양', '자연이공계기초', '확대교양' 중
    하나의 표준 키를 반환한다. 매핑이 없으면 빈 문자열.
    """
    mapping = {
        "개신기초교양": "개신기초교양",
        "일반교양": "일반교양",
        "자연이공계기초과학": "자연이공계기초과학",
        "확대교양": "확대교양",
    }

    cat = getattr(course, "category", None)
    while cat:
        name = cat.category_name
        if name in mapping:
            return mapping[name]
        cat = cat.parent_category  # 위로 한 단계
    return ""


# ------------------------------------
# 2. 미이수 전공필수 과목 추출 함수 (변경 없음)
def extract_missing_required_major_courses(user_dept_id, completed_courses):
    """
    사용자 전공(dept_id)에 해당하는 전공필수 강좌 중,
    이미 이수한 과목(completed_courses 집합)에 포함되지 않은 고유 course_name(대문자 기준)들을 반환.
    """

    svc = CourseFilterService()
    user_dept_name = Department.objects.get(pk=user_dept_id) # 학과(학부) 이름 조회

    missing_courses = set()
    required_courses = svc.course_search(category_name='전공필수', dept_name=user_dept_name)
    for course in required_courses:
        cname = course.course_name.strip().upper()
        if cname not in completed_courses:
            missing_courses.add(cname)
    return missing_courses



def apply_time_constraints(candidate_data, only_ranges, avoid_times, avoid_ranges):
    """
    candidate_data: [{'id', 'schedule':[{'day','times',…},…],…}, …]
    only_ranges: [{"days":[..], "start_hour":int, "end_hour":int?}, …]
    avoid_times: [{"day":str,"hour":int}, …]
    avoid_ranges: [{"days":[..], "start_hour":int, "end_hour":int?}, …]
    """
    # 1) only_time_ranges 적용 — 있으면 이 범위 **외** 과목 제거
    if only_ranges:
        filtered = []
        for data in candidate_data:
            ok = True
            for sched in data['schedule']:
                # times: "02,03,04" → [10,11,12]
                hours = [int(t)+8 for t in sched['times'].split(',')]
                if not any(
                    sched['day'] in r['days']
                    and all(h >= r['start_hour'] and
                            ('end_hour' not in r or h < r['end_hour'])
                        for h in hours)
                    for r in only_ranges
                ):
                    ok = False
                    break
            if ok:
                filtered.append(data)
        candidate_data = filtered

    # 2) avoid_times / avoid_time_ranges 적용 — 걸리면 제거
    if avoid_times or avoid_ranges:
        filtered = []
        for data in candidate_data:
            bad = False
            for sched in data['schedule']:
                hours = [int(t)+8 for t in sched['times'].split(',')]
                # (1) 단일 시각 회피
                if any(obj['day']==sched['day'] and h==obj['hour'] 
                       for obj in avoid_times for h in hours):
                    bad = True
                    break
                # (2) 범위 회피
                if any(
                    sched['day'] in r['days']
                    and any(h >= r['start_hour'] and
                            ('end_hour' not in r or h < r['end_hour'])
                        for h in hours)
                    for r in avoid_ranges
                ):
                    bad = True
                    break
            if not bad:
                filtered.append(data)
        candidate_data = filtered

    return candidate_data



# ------------------------------------
# 3. generate_timetable_stream 함수 (교양의 parent_category 조건 추가)
def generate_timetable_stream(request):
    year = 2025
    term = '1학기'
    try:
        print("DEBUG: --- Timetable Generation Start ---")

        # 0) 자연어 파싱으로 받아온 필수 과목명 → Course ID 리스트(req_ids)
        req_names = request.GET.getlist('required_courses[]')
        req_ids = []
        
        svc = CourseFilterService()
        # 미리 연도·학기·카테고리를 넣어서 기본 queryset을 받아옵니다.
        major_qs = (
            svc.course_search(year=year, term=term, category_name='전공필수') |
            svc.course_search(year=year, term=term, category_name='전공선택') |
            svc.course_search(year=year, term=term, category_name='교양선택')
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
        try:
            pre_added_ids = [int(cid) for cid in existing_ids]
        except ValueError:
            pre_added_ids = []

        # 2) OpenAI로 파싱된 req_ids를 꼭 포함되도록 합치기 & 중복 제거
        pre_added_ids = list(set(pre_added_ids + req_ids))
        print("DEBUG: final pre_added_ids (기존+필수과목) =", pre_added_ids)

        try:
            target_major    = int(request.GET.get('major_credits', 9))
            target_elective = int(request.GET.get('elective_credits', 9))
            # 전공+교양 합계를 총 학점으로 강제
            target_total    = target_major + target_elective
            print("DEBUG: auto target_total =", target_total)
        except ValueError:
            return JsonResponse({"error": "학점 파라미터가 올바르지 않습니다."}, status=500)

        print("DEBUG: free_days =", free_days)
        print("DEBUG: target_total =", target_total,
            "target_major =", target_major,
            "target_elective =", target_elective)
        
        # 2) 신규: 시간 제약조건 파싱
        only_ranges  = [json.loads(s) for s in request.GET.getlist('only_time_ranges[]')]
        avoid_times  = [json.loads(s) for s in request.GET.getlist('avoid_times[]')]
        avoid_ranges = [json.loads(s) for s in request.GET.getlist('avoid_time_ranges[]')]
        print("DEBUG: only_time_ranges =", only_ranges)
        print("DEBUG: avoid_times =", avoid_times)
        print("DEBUG: avoid_time_ranges =", avoid_ranges)

        # 3) 미리 추가된 과목(CP-SAT 모델에 강제로 포함)
        svc = CourseFilterService()
        pre_added_courses = list(Courses.objects.filter(course_id__in=pre_added_ids))
        print("DEBUG: pre_added_courses count =", len(pre_added_courses))
        # 3-3. 학생 정보 및 졸업 기록 로드

        # 사용자가 공강(free_days)을 요청했으면,
        # 기존에 추가된(pre_added) 과목 중 free_days 요일에 속한 과목은 제외
        if free_days:
            filtered = []
            for course in pre_added_courses:
                # 해당 과목의 모든 스케줄 중에 free_days에 해당하는 day가 있으면 제거
                if not any(sch.day in free_days for sch in course.courseschedule_set.all()):
                    filtered.append(course)
            dropped = set(pre_added_ids) - set(c.course_id for c in filtered)
            if dropped:
                print("DEBUG: dropped pre_added courses on free_days:", dropped)
            pre_added_courses = filtered
            # pre_added_ids 도 함께 갱신
            pre_added_ids = [c.course_id for c in pre_added_courses]

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
        
        candidate_qs = (( svc.course_search(year= year, term = term, category_name='전공')
                        | svc.course_search(year= year, term = term, category_name='교양')
                        ).annotate(upper_course_name=Upper('course_name')).exclude(upper_course_name__in=[name.upper() for name in completed_courses]))

        candidates = []
        for course in candidate_qs:
            # ----- 전공 과목 필터 -----
            if course.category.category_name in ["전공필수", "전공선택"]:
                if course.target_year != "전학년":  # CHANGED
                    try:
                        course_year = int(course.target_year[0])  # CHANGED
                    except Exception:
                        course_year = 0
                    if course_year > current_year:
                        continue

                # 학과 일치 여부
                # 소프트웨어학과, 소프트웨어학부는 같은 학과로 보고 예외처리..
                # 왜냐하면 예를들어 나(노혜성)은 소프트웨어학과로 들어와서 소속은 소프트웨어학과지만
                # 현재 소프트웨어학과는 소프트웨어학부로 바뀌었기 떄문
                if student_dept_id == 48:  # 소프트웨어학과
                    student_dept_id = 50 # 소프트웨어학부

                if student_dept_id and course.dept_id and course.dept_id != student_dept_id:
                    continue

            # ----- 기본 필터 -----
            if course.course_id in pre_added_ids:
                continue
            if course.credits <= 0:  # CHANGED
                continue
            # 시간표 '00' slot 제거
            if any(sch.times.strip() == "00" for sch in course.courseschedule_set.all()):  # CHANGED
                continue
            # Free‑day 충돌
            if any(sch.day in free_days for sch in course.courseschedule_set.all()):  # CHANGED
                continue
            # 교양은 target_year가 전학년이어야
            if get_effective_general_category(course) and course.target_year != "전학년":  # CHANGED
                continue
            if any("가상강의실" in (sch.location or "") for sch in course.courseschedule_set.all()):
                continue
            # 추가 필터: 교양 강좌(구 교양선택)의 경우, 해당 세부 항목의 남은 학점이 0이면 후보에서 제외
            if get_effective_general_category(course):
                effective_cat = get_effective_general_category(course)
                if missing_gen_sub.get(effective_cat, 0) == 0:
                    # print("DEBUG: Excluding 교양 course", course.course_name, "as", effective_cat, "is already completed.")
                    continue

            candidates.append(course)

        all_candidates = pre_added_courses + candidates
        print("DEBUG: candidates count =", len(candidates))
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
                'credit': course.credits,
                'category': course.category.category_name,  # course_type
                'course_name': course.course_name,
                'year': course.target_year,
                'schedule': schedule_list,
                'location': locations[0] if locations else "",
                'pre_added': course.course_id in pre_added_ids
            }
            # 교양 강좌: effective_category 추가
            if get_effective_general_category(course):
                data_item['effective_category'] = get_effective_general_category(course)
            candidate_data.append(data_item)
        print("DEBUG: candidate_data count =", len(candidate_data))
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
                if ok: filtered.append(d)
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
                        bad = True; break
                    if any(
                        sched['day'] in r['days']
                        and any(in_range(h, r['start_hour'], r.get('end_hour')) for h in hours)
                        for r in avoid_ranges
                    ):
                        bad = True; break
                if not bad: filtered.append(d)
            candidate_data = filtered
            print("DEBUG: avoid_times/avoid_time_ranges 적용 후 count =", len(candidate_data))

        # ===== 수정된 부분: 전공선택 강좌 중 동일학년 강좌 우선 필터링 =====
        for data in candidate_data:
            if data['category'] == '전공선택':
                if data['year'] == "전학년" or (
                        data['year'] and data['year'][0].isdigit() and int(data['year'][0]) == current_year):
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
        # --- NEW: exclude_courses 적용 ---
        if exclude_names:
            filtered = []
            for d in candidate_data:
                # d['course_name'] 안에 제외할 이름이 포함되면 걸러냄
                if not any(name in d['course_name'] for name in exclude_names):
                    filtered.append(d)
            candidate_data = filtered
            print("DEBUG: after exclude_courses filter:", len(candidate_data))
        # 4. CP‑SAT 모델 구성 (후속 부분은 기존과 동일)
        model = cp_model.CpModel()
        x = {}
        for data in candidate_data:
            x[data['id']] = model.NewBoolVar(f"course_{data['id']}")

        for data in candidate_data:
            if data.get('pre_added', False):
                model.Add(x[data['id']] == 1)

        model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data) == target_total)
        model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data if
                    data['category'] in ['전공필수', '전공선택']) == target_major)
        model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data if get_effective_general_category(
            course=DummyObj({'effective': data.get('effective_category', None)})) or data['category'] not in ['전공필수',
                                                                                                            '전공선택']) == target_elective)

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
            if data['category'] == '전공필수' and (
                        data['year'] == "전학년" or (data['year'][0].isdigit() and int(data['year'][0]) <= current_year))
        )
        elective_priority = 0.1 * sum(
            x[data['id']] for data in candidate_data
            if data['category'] == '전공선택' and (
                        data['year'] == "전학년" or (data['year'][0].isdigit() and int(data['year'][0]) == current_year))
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
        model2.Add(sum(data['credit'] * x2[data['id']] for data in candidate_data if
                    data['category'] in ['전공필수', '전공선택']) == target_major)
        model2.Add(sum(data['credit'] * x2[data['id']] for data in candidate_data if get_effective_general_category(
            course=DummyObj({'effective': data.get('effective_category', None)})) or data['category'] not in ['전공필수',
                                                                                                            '전공선택']) == target_elective)

        for (day, slot), ids in slot_mapping.items():
            model2.Add(sum(x2[cid] for cid in ids) <= 1)
        for name, ids in name_groups.items():
            model2.Add(sum(x2[cid] for cid in ids) <= 1)
        model2.Add(sum(x2[data['id']] for data in candidate_data
                    if data['category'] == '전공필수' and (data['year'] == "전학년" or (
                    data['year'][0].isdigit() and int(data['year'][0]) <= current_year))) == int(best_value))
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
    except Exception as e:
        traceback.print_exc()  # 서버 콘솔에 full traceback
        # 클라이언트에서 읽어볼 수 있도록 간단한 JSON으로도 리턴
        return JsonResponse({"error": str(e)}, status=500)
def manage_view(request):
    return render(request, "home/manage.html")