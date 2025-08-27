import os
import traceback
from collections import defaultdict

from django.contrib.auth import logout
from django.db.models.functions import Upper
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render, redirect
from django.conf import settings
from data_manager.services.course_filter_service import CourseFilterService
from data_manager.models import *
from .forms import CustomUserCreationForm
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse_lazy

from .services.gpt_service import extract_graduation_info_from_text
from .services.graduation_file_service import save_graduation_data_to_db
from data_manager.services.graduation_engine import GraduationEngine
from .services.pdf_service import pdf_to_text
from django.views.decorators.csrf import csrf_exempt

import json

from ortools.sat.python import cp_model

import re
import requests


# Rasa 서버 URL 설정
RASA_MODEL_ENDPOINT = "http://localhost:5005/model/parse"  # Rasa NLU 서버 URL
RASA_WEBHOOK_ENDPOINT = "http://localhost:5005/webhooks/rest/webhook"  # Rasa 대화 서버 URL

# views.py 
@csrf_exempt
def parse_constraints(request):
    data = json.loads(request.body)
    user_text = data.get("text", "")
    session_id = data.get("session_id", "default_user")

    print(request.body)

    # 1) 직접 Rasa 서버의 웹훅에 요청보내기
    try:
        rasa_response = requests.post(
            RASA_WEBHOOK_ENDPOINT,
            json={
                "sender": session_id,
                "message": user_text
            }
        )
        
        if rasa_response.status_code != 200:
            print('111')
            return JsonResponse({"error": f"Rasa 서버 응답 오류: {rasa_response.status_code}"}, status=500)
        
        # Rasa 응답 반환 (웹훅 형식)
        return JsonResponse(rasa_response.json(), safe=False)
        
    except Exception as e:
        print(str(e))
        return JsonResponse({"error": f"Rasa 서버 연결 오류: {str(e)}"}, status=500)
    
    # 2) 또는 model/parse 엔드포인트 이용 (NLU만)
    """
    try:
        rasa_response = requests.post(
            RASA_MODEL_ENDPOINT,
            json={"text": user_text}
        )
        
        if rasa_response.status_code != 200:
            return JsonResponse({"error": f"Rasa 서버 응답 오류: {rasa_response.status_code}"}, status=500)
        
        # Rasa NLU 응답에서 필요한 정보 추출
        rasa_data = rasa_response.json()
        intent = rasa_data.get("intent", {}).get("name", "")
        entities = rasa_data.get("entities", [])
        
        # 엔티티 매핑 및 처리
        constraints = {}
        
        for entity in entities:
            entity_type = entity["entity"]
            value = entity["value"]
            
            if entity_type == "major_credits_entity":
                value_num = re.findall(r'\d+', value)
                if value_num:
                    constraints["major_credits"] = int(value_num[0])
            
            elif entity_type == "elective_credits_entity":
                value_num = re.findall(r'\d+', value)
                if value_num:
                    constraints["elective_credits"] = int(value_num[0])
            
            elif entity_type == "course_name_entity":
                if "required_courses" not in constraints:
                    constraints["required_courses"] = []
                constraints["required_courses"].append(value)
            
            elif entity_type in ["free_day_entity", "free_day_keyword_entity"]:
                if "free_days" not in constraints:
                    constraints["free_days"] = []
                
                # 한글 요일을 약자로 변환
                day_mapping = {"월요일": "월", "화요일": "화", "수요일": "수", "목요일": "목", "금요일": "금"}
                day = day_mapping.get(value, value)
                if day in ["월", "화", "수", "목", "금"] and day not in constraints["free_days"]:
                    constraints["free_days"].append(day)
        
        return JsonResponse(constraints)
        
    except Exception as e:
        return JsonResponse({"error": f"Rasa 서버 연결 오류: {str(e)}"}, status=500)
    """

def extract_constraints_from_rasa_response(rasa_response):
    """Rasa NLU 응답에서 시간표 제약조건을 추출합니다."""
    constraints = {
        "major_credits": None,
        "elective_credits": None,
        "required_courses": [],
        "free_days": [],
        "avoid_times": [],
        "avoid_time_ranges": [],
        "only_time_ranges": [],
        "exclude_courses": []
    }
    
    # 1. 엔티티 처리
    entities = rasa_response.get("entities", [])
    for entity in entities:
        entity_type = entity["entity"]
        value = entity["value"]
        
        if entity_type == "major_credits_entity":
            constraints["major_credits"] = extract_number(value)
        
        elif entity_type == "elective_credits_entity":
            constraints["elective_credits"] = extract_number(value)
        
        elif entity_type == "course_name_entity":
            # 2. 인텐트에 따라 처리 방식 결정
            intent = rasa_response.get("intent", {}).get("name", "")
            if intent == "modify_timetable":
                # 수정 요청일 경우: 과목 제외 목록에 추가
                if value not in constraints["exclude_courses"]:
                    constraints["exclude_courses"].append(value)
            else:
                # 일반 요청: 필수 과목 목록에 추가
                if value not in constraints["required_courses"]:
                    constraints["required_courses"].append(value)
        
        elif entity_type == "free_day_entity":
            day = get_korean_day_abbr(value)
            if day and day not in constraints["free_days"]:
                constraints["free_days"].append(day)
        
        elif entity_type == "free_day_keyword_entity":
            day = get_korean_day_abbr(value)
            if day and day not in constraints["free_days"]:
                constraints["free_days"].append(day)
        
        elif entity_type == "time_entity":
            # 시간 회피 처리 (예: "월요일 9시 피해줘")
            # 필요한 추가 컨텍스트 분석이 있다면 여기에 구현
            hour = extract_number(value)
            
            # 직전 엔티티가 요일인지 확인하는 로직이 필요할 수 있음
            # 간소화된 구현: 마지막으로 언급된 요일에 적용
            if hour is not None and constraints["free_days"]:
                last_day = constraints["free_days"][-1]
                constraints["avoid_times"].append({"day": last_day, "hour": hour})
        
        elif entity_type == "time_range_entity":
            # 시간대 회피 처리 (예: "오후 수업 피해줘")
            time_range = parse_time_range(value)
            if time_range:
                # 모든 요일 또는 특정 요일에 적용
                days = constraints["free_days"] if constraints["free_days"] else ["월", "화", "수", "목", "금"]
                time_range["days"] = days
                constraints["avoid_time_ranges"].append(time_range)

    return constraints


def extract_number(text):
    """텍스트에서 숫자를 추출합니다."""
    if not text:
        return None
    
    # 숫자 추출 정규식
    numbers = re.findall(r'\d+', text)
    if numbers:
        return int(numbers[0])
    return None


def get_korean_day_abbr(day_text):
    """한글 요일 전체 이름을 약자로 변환합니다."""
    day_text = str(day_text).strip().lower()
    mapping = {
        "월요일": "월", "화요일": "화", "수요일": "수", "목요일": "목", "금요일": "금",
        "월": "월", "화": "화", "수": "수", "목": "목", "금": "금",
        "월공강": "월", "화공강": "화", "수공강": "수", "목공강": "목", "금공강": "금",
    }
    
    for key, value in mapping.items():
        if key in day_text:
            return value
    return day_text


def parse_time_range(time_text):
    """시간대 텍스트를 시간 범위로 변환합니다."""
    if "오전" in time_text:
        return {"start_hour": 9, "end_hour": 12}
    elif "오후" in time_text:
        return {"start_hour": 13, "end_hour": 18}
    return None

class CustomLoginView(LoginView):
    template_name = 'home/login.html'
    authentication_form = AuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # ?next= 우선, 없으면 대시보드로 이동
        
        return self.get_redirect_url() or reverse_lazy('dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 회원가입 폼이 없으면 추가
        if 'register_form' not in context:
            context['register_form'] = CustomUserCreationForm()
        return context

def logout_view(request):
    logout(request)
    return redirect('/')

def index_view(request):
    # 로그인 여부를 판단하고, 로그인 페이지 혹은 대쉬보드 페이지로 이동
    if request.user.is_authenticated:
        return render(request, 'home/dashboard.html')
    else:
        return render(request, 'home/index.html')

def course_serach_test_view(request):
    return render(request, 'home/search_test.html')

def timetable_view(request):
    return render(request, "home/timetable/timetable.html")

def dashboard_view(request):
    return render(request, 'home/dashboard.html')

def mypage_view(request):
    context = {}

    # 사용자 학사 정보는 UserProfile에서 가져오기
    user_profile = None
    if request.user.is_authenticated:
        user_profile = UserProfile.objects.filter(user=request.user).select_related('department').first()

    context['user_student_id'] = getattr(user_profile, 'user_student_id', "") if user_profile else ""
    context['user_name'] = getattr(user_profile, 'user_name', "") if user_profile else ""
    context['user_major'] = (user_profile.department.dept_name if getattr(user_profile, 'department', None) else "") if user_profile else ""
    # 학년 표기: 숫자면 "n학년"으로, 없으면 빈 문자열
    if user_profile and getattr(user_profile, 'current_grade', None) is not None:
        try:
            context['user_year'] = f"{int(user_profile.current_grade)}학년"
        except Exception:
            context['user_year'] = str(user_profile.current_grade)
    else:
        context['user_year'] = ""

    # 사용자 이수내역(Transcript)과 졸업엔진 결과(알림/요건) 제공 =====
    # Course History 집계
    try:
        course_history = []
        transcripts = []
        if user_profile:
            transcripts = list(
                Transcript.objects.filter(user_profile=user_profile)
                .select_related('course__semester', 'course__category')
            )
            for t in transcripts:
                c = t.course
                sem = getattr(c, 'semester', None)
                year = getattr(sem, 'year', None)
                term = getattr(sem, 'term', '')
                # 카테고리 간소화 명칭 활용
                course_type = get_simplified_category_name(c) if callable(get_simplified_category_name) else (c.category.category_name if c.category else '')
                course_history.append({
                    'year': year if year is not None else 0,
                    'term': term or '',
                    'course_code': c.course_code,
                    'course_name': c.course_name,
                    'credit': int(getattr(c, 'credits', 0)),
                    'course_type': course_type,
                    'grade': t.grade,
                })
        context['course_history_json'] = json.dumps(course_history, ensure_ascii=False)
    except Exception:
        context['course_history_json'] = json.dumps([], ensure_ascii=False)

    # 졸업 요건 엔진 실행 및 알림/요건 트리 생성
    try:
        requirements_tree = []
        engine_alerts = []
        if user_profile and transcripts:
            engine = GraduationEngine(user_profile=user_profile, transcripts=transcripts)
            # 알림(remark) 수집
            try:
                results = engine.run()
                for r in results:
                    # r는 RuleResult dataclass (is_satisfied, remark 등 포함)
                    if getattr(r, 'remark', '') and not getattr(r, 'is_satisfied', True):
                        engine_alerts.append(r.remark)
            except Exception:
                pass

            # 계층형 요건 트리 구성: 규칙 카테고리 및 조상 노드만 표시
            try:
                categories_map = engine.categories_map or {}
                credits_by_category = engine.processed_data.get('credits_by_category', {}) if hasattr(engine, 'processed_data') else {}
                rules_qs = engine.ruleset.rules.select_related('category').all() if getattr(engine, 'ruleset', None) else []
                required_by_cat_id = {}
                rule_cat_ids = set()
                for rule in rules_qs:
                    cid = rule.category.category_id
                    rule_cat_ids.add(cid)
                    # 동일 카테고리의 규칙이 여러 개면 필요한 최소 학점을 합산
                    required_by_cat_id[cid] = required_by_cat_id.get(cid, 0) + int(getattr(rule, 'min_credits', 0) or 0)

                # 표시 대상 카테고리 집합(규칙 카테고리 + 모든 조상)
                display_ids = set()
                for cid in rule_cat_ids:
                    current = categories_map.get(cid)
                    while current:
                        display_ids.add(current.category_id)
                        parent_id = getattr(current, 'parent_category_id', None)
                        if not parent_id:
                            break
                        current = categories_map.get(parent_id)

                # children 매핑 구성
                children_by_parent = {}
                for cid in display_ids:
                    cat = categories_map.get(cid)
                    if not cat:
                        continue
                    parent_id = getattr(cat, 'parent_category_id', None)
                    if parent_id in display_ids:
                        children_by_parent.setdefault(parent_id, []).append(cid)

                # 노드 생성
                def build_node(cid):
                    cat = categories_map.get(cid)
                    if not cat:
                        return None
                    earned = float(credits_by_category.get(cid, 0.0))
                    required = required_by_cat_id.get(cid)
                    node = {
                        'id': cid,
                        'name': cat.category_name,
                        'level': int(getattr(cat, 'category_level', 0) or 0),
                        'earned': round(earned, 2),
                        'required': int(required) if required is not None else None,
                        'children': []
                    }
                    # 정렬된 자식 노드 구성
                    child_ids = sorted(children_by_parent.get(cid, []), key=lambda x: (getattr(categories_map.get(x), 'category_level', 0) or 0, categories_map.get(x).category_name if categories_map.get(x) else ''))
                    for child_id in child_ids:
                        child_node = build_node(child_id)
                        if child_node:
                            node['children'].append(child_node)
                    return node

                # 루트(표시 대상 중 상위) 추출 및 트리 생성
                root_ids = []
                for cid in display_ids:
                    cat = categories_map.get(cid)
                    parent_id = getattr(cat, 'parent_category_id', None) if cat else None
                    if parent_id not in display_ids:
                        root_ids.append(cid)
                root_ids.sort(key=lambda x: (getattr(categories_map.get(x), 'category_level', 0) or 0, categories_map.get(x).category_name if categories_map.get(x) else ''))

                for root_id in root_ids:
                    node = build_node(root_id)
                    if node:
                        requirements_tree.append(node)
            except Exception:
                requirements_tree = []

        # 기존 alerts에 엔진 알림 병합
        if engine_alerts:
            context['alerts'] = list(context.get('alerts', []) or []) + engine_alerts

        context['requirements_tree_json'] = json.dumps(requirements_tree, ensure_ascii=False)
    except Exception:
        context['requirements_tree_json'] = json.dumps([], ensure_ascii=False)

    print(context)

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


def get_simplified_category_name(course):
    """
    강의의 카테고리를 상위 분류로 통일하는 함수
    교양 과목의 경우 level 2(세부분류)를 level 1(상위분류)로 변경
    예: "인간과문화" -> "일반교양"
    """
    if not course.category:
        return None
    
    category = course.category
    
    # 카테고리 레벨이 2이고, 부모의 부모가 "교양"인 경우
    if (category.category_level == 2 and 
        category.parent_category and 
        category.parent_category.parent_category and 
        category.parent_category.parent_category.category_name == "교양"):
        # 부모 카테고리(level 1)의 이름을 반환
        return category.parent_category.category_name
    
    # 그 외의 경우는 원래 카테고리 이름 반환
    return category.category_name


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



def apply_time_constraints(candidate_data, only_ranges, avoid_times, avoid_ranges, specific_avoid_times=None, specific_avoid_time_ranges=None):
    """
    candidate_data: [{'id', 'schedule':[{'day','times',…},…],…}, …]
    only_ranges: [{"days":[..], "start_hour":int, "end_hour":int?}, …]
    avoid_times: [{"day":str,"hour":int}, …]
    avoid_ranges: [{"days":[..], "start_hour":int, "end_hour":int?}, …]
    specific_avoid_times: [{"day":str,"hour":int}, …] (특정 요일+시간)
    specific_avoid_time_ranges: [{"day":str,"start_hour":int,"end_hour":int}, …] (특정 요일+시간범위)
    """
    if specific_avoid_times is None:
        specific_avoid_times = []
    if specific_avoid_time_ranges is None:
        specific_avoid_time_ranges = []
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

    # 3) specific_avoid_times / specific_avoid_time_ranges 적용 — 특정 요일+시간 회피
    if specific_avoid_times or specific_avoid_time_ranges:
        filtered = []
        for data in candidate_data:
            bad = False
            for sched in data['schedule']:
                hours = [int(t)+8 for t in sched['times'].split(',')]
                
                # (1) 특정 요일+시간 회피
                if any(obj['day']==sched['day'] and h==obj['hour'] 
                       for obj in specific_avoid_times for h in hours):
                    bad = True
                    print(f"DEBUG: 특정 시간 회피로 과목 제외 - {data.get('course_name', 'Unknown')} ({sched['day']}요일 {hours}시)")
                    break
                
                # (2) 특정 요일+시간범위 회피
                if any(
                    obj['day']==sched['day']
                    and any(h >= obj['start_hour'] and h < obj['end_hour']
                        for h in hours)
                    for obj in specific_avoid_time_ranges
                ):
                    bad = True
                    print(f"DEBUG: 특정 시간범위 회피로 과목 제외 - {data.get('course_name', 'Unknown')} ({sched['day']}요일 {hours}시)")
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
        try:
            pre_added_ids = [int(cid) for cid in existing_ids]
        except ValueError:
            pre_added_ids = []

        pre_added_ids = list(set(pre_added_ids + req_ids))
        print("DEBUG: final pre_added_ids (기존+필수과목) =", pre_added_ids)

        try:
            target_total    = int(request.GET.get('total_credits', 18))
            target_major    = int(request.GET.get('major_credits', 9))
            target_elective = int(request.GET.get('elective_credits', 9))
            
            # 전공 + 교양 학점이 총 학점을 초과하지 않도록 조정
            if target_major + target_elective > target_total:
                # 비율에 따라 조정
                ratio = target_total / (target_major + target_elective)
                target_major = int(target_major * ratio)
                target_elective = target_total - target_major
                print(f"DEBUG: 학점 조정됨 (초과) - 전공: {target_major}, 교양: {target_elective}")
            # 전공 + 교양 학점이 총 학점보다 작은 경우는 그대로 유지 (사용자 의도 존중)
            # elif target_major + target_elective < target_total:
            #     # 부족한 학점은 교양에 추가 - 이 로직을 제거하여 사용자 설정 존중
            #     target_elective = target_total - target_major
            #     print(f"DEBUG: 교양 학점 증가 - 교양: {target_elective}")
            
            # 실제 목표 학점을 전공 + 교양 학점의 합으로 설정 (사용자 의도 존중)
            actual_total = target_major + target_elective
            if actual_total != target_total:
                print(f"DEBUG: 실제 목표 학점 조정 - 요청: {target_total}, 실제: {actual_total}")
                target_total = actual_total
            
            print("DEBUG: 최종 학점 설정 - total:", target_total, "major:", target_major, "elective:", target_elective)
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
        
        # 특정 시간대 공강 파라미터 추가
        specific_avoid_times = [json.loads(s) for s in request.GET.getlist('specific_avoid_times[]')]
        specific_avoid_time_ranges = [json.loads(s) for s in request.GET.getlist('specific_avoid_time_ranges[]')]
        
        print("DEBUG: only_time_ranges =", only_ranges)
        print("DEBUG: avoid_times =", avoid_times)
        print("DEBUG: avoid_time_ranges =", avoid_ranges)
        print("DEBUG: specific_avoid_times =", specific_avoid_times)
        print("DEBUG: specific_avoid_time_ranges =", specific_avoid_time_ranges)

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
            # ----- 제외할 과목 필터 (과목 코드로 처리) -----
            if exclude_names:
                should_exclude = False
                # 과목 코드로 제외 처리 (더 정확함)
                course_id_str = str(course.course_id)
                for exclude_item in exclude_names:
                    exclude_item_str = str(exclude_item).strip()
                    # 과목 코드로 정확히 매칭
                    if course_id_str == exclude_item_str:
                        should_exclude = True
                        print(f"DEBUG: 과목 제외됨 (ID 매칭) - '{course.course_name}' (ID: {course.course_id}, 제외 조건: '{exclude_item}')")
                        break
                    # 과목명으로도 매칭 (하위 호환성)
                    elif not exclude_item_str.isdigit():
                        course_name_lower = course.course_name.lower().strip()
                        exclude_name_lower = exclude_item_str.lower().strip()
                        if (course_name_lower == exclude_name_lower or 
                            exclude_name_lower in course_name_lower or 
                            course_name_lower in exclude_name_lower):
                            should_exclude = True
                            print(f"DEBUG: 과목 제외됨 (이름 매칭) - '{course.course_name}' (제외 조건: '{exclude_item}')")
                            break
                if should_exclude:
                    continue
            
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
                'course_name': course.course_name,
                'course_code': course.course_code,
                'section': course.section,
                'credit': course.credits, # CP-SAT 모델은 'credit'을 사용하므로 일단 유지
                'credits': course.credits, # 프론트엔드를 위해 'credits'도 추가
                'year': course.target_year ,
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

        # specific_avoid_times / specific_avoid_time_ranges: 특정 요일+시간 회피 조건 제거
        if specific_avoid_times or specific_avoid_time_ranges:
            filtered = []
            for d in candidate_data:
                bad = False
                for sched in d['schedule']:
                    hours = [int(t)+8 for t in sched['times'].split(',') if t.strip().isdigit()]
                    
                    # (1) 특정 요일+시간 회피
                    if any(obj['day']==sched['day'] and h==obj['hour'] 
                           for obj in specific_avoid_times for h in hours):
                        bad = True
                        print(f"DEBUG: 특정 시간 회피로 과목 제외 - {d.get('course_name', 'Unknown')} ({sched['day']}요일 {hours}시)")
                        break
                    
                    # (2) 특정 요일+시간범위 회피
                    if any(
                        obj['day']==sched['day']
                        and any(h >= obj['start_hour'] and h < obj['end_hour']
                            for h in hours)
                        for obj in specific_avoid_time_ranges
                    ):
                        bad = True
                        break
                if not bad: 
                    filtered.append(d)
            candidate_data = filtered
            print("DEBUG: specific_avoid_times/specific_avoid_time_ranges 적용 후 count =", len(candidate_data))

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
        # --- NEW: exclude_courses 적용 (개선된 버전) ---
        if exclude_names:
            print("DEBUG: Applying exclude_courses filter:", exclude_names)
            filtered = []
            for d in candidate_data:
                course_name = d['course_name'].strip()
                should_exclude = False
                
                # 각 제외할 과목명에 대해 정확한 매칭 및 부분 매칭 확인
                for exclude_name in exclude_names:
                    exclude_name = exclude_name.strip()
                    if not exclude_name:
                        continue
                    
                    # 1. 정확한 매칭 (대소문자 무시)
                    if course_name.lower() == exclude_name.lower():
                        should_exclude = True
                        print(f"DEBUG: Exact match exclusion: '{course_name}' == '{exclude_name}'")
                        break
                    
                    # 2. 부분 매칭 (제외할 이름이 과목명에 포함)
                    if exclude_name.lower() in course_name.lower():
                        should_exclude = True
                        print(f"DEBUG: Partial match exclusion: '{exclude_name}' in '{course_name}'")
                        break
                    
                    # 3. 역방향 부분 매칭 (과목명이 제외할 이름에 포함)
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
                # candidate_data를 id를 키로 하는 딕셔너리로 변환하여 쉽게 접근
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
                        # self._candidate_data에서 해당 강의의 전체 정보를 가져옵니다.
                        data = self._candidate_data[cid]

                        solution.append({
                            # --- 기존 필드명과 구조를 프론트엔드 Course 클래스에 맞게 수정 ---
                            'course_id': data['id'],
                            'course_name': data.get('course_name', ''),
                            'course_code': data.get('course_code', ''),  # 누락된 필드 추가
                            'section': data.get('section', ''),  # 누락된 필드 추가
                            'credits': data.get('credit', 0),  # 'credit' -> 'credits'로 변경
                            'target_year': data.get('year', ''),  # 'year' -> 'target_year'로 변경
                            'instructor_name': data.get('instructor_name', ''),  # 누락된 필드 추가
                            'capacity': data.get('capacity', 0),  # 누락된 필드 추가
                            'dept_name': data.get('dept_name', ''),  # 누락된 필드 추가
                            'category_name': data.get('category', ''),  # 'category' -> 'category_name'으로 변경
                            'semester': data.get('semester', ''),  # 누락된 필드 추가
                            'schedules': data.get('schedule', []),
                            # 필드명은 'schedule' -> 'schedules'가 더 명확하나, 기존 코드가 schedule을 사용하므로 유지하거나 양쪽 모두 수정 필요. 여기서는 일단 유지.
                            'location': data.get('location', '')
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
    """시간표 관리 페이지 - 새로운 테이블 구조 사용"""
    # 저장된 시간표 목록을 가져와서 전달
    user_id = request.user.id if request.user.is_authenticated else 8  # 테스트용으로 8 사용
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
    
    return render(request, "home/manage.html", {
        'timetables': timetables_data,
        'timetables_json': timetables_json
    })


@csrf_exempt
def save_timetable(request):
    """시간표 저장 API - 새로운 테이블 구조 사용"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST 요청만 허용됩니다.'}, status=405)
    
    try:
        data = json.loads(request.body)
        courses = data.get('courses', [])
        title = data.get('title', '')
        
        print(f"시간표 저장 요청 받음: {len(courses)}개 과목")
        print(f"요청 데이터: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # 사용자 정보 가져오기
        user_id = request.user.id if request.user.is_authenticated else 8  # 테스트용으로 8 사용
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
            print(f"과목 스케줄: {schedules}")
            
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
                
                # 시작/종료 시간 계산 (times가 "02,03,04" 형태라고 가정)
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
    """시간표 삭제 API - 새로운 테이블 구조 사용"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'DELETE 요청만 허용됩니다.'}, status=405)
    
    try:
        user_id = request.user.id if request.user.is_authenticated else 8  # 테스트용으로 8 사용
        timetable = SavedTimetable.objects.filter(
            id=timetable_id,
            user_id=user_id
        ).first()
        
        if not timetable:
            return JsonResponse({'error': '시간표를 찾을 수 없습니다.'}, status=404)
        
        print(f"시간표 삭제: {timetable.title} (ID: {timetable_id})")
        timetable.delete()  # CASCADE로 관련 데이터도 자동 삭제됨
        
        return JsonResponse({
            'success': True,
            'message': '시간표가 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        print(f"시간표 삭제 오류: {str(e)}")
        return JsonResponse({'error': f'시간표 삭제 중 오류가 발생했습니다: {str(e)}'}, status=500)


def review_detail_page(request, summary_id):
    """특정 강의 리뷰 요약에 대한 사용자 코멘트 페이지를 렌더링합니다."""
    # summary_id를 템플릿으로 전달하여 JS에서 사용할 수 있도록 합니다.
    # 실제 데이터 로딩은 JS에서 API를 통해 이루어집니다.
    return render(request, 'home/review_detail_page.html', {'summary_id_from_view': summary_id})


from data_manager.services.review_service import ReviewService


def review_search_summary_view(request):
    search_query_course_name = request.GET.get('course_name', '')
    search_query_instructor_name = request.GET.get('instructor_name', '')
    search_query_course_code = request.GET.get('course_code', '')
    selected_summary_id = request.GET.get('summary_id')

    search_results = []
    selected_summary = None

    review_service = ReviewService()

    # 1. summary_id가 직접 제공된 경우, 우선적으로 해당 요약 정보 로드
    if selected_summary_id:
        summary_queryset = review_service.get_reviews(summary_id=selected_summary_id)
        selected_summary = summary_queryset.first()
        # 이 경우, 다른 검색 조건이 있더라도 selected_summary_id를 우선하므로,
        # search_results는 selected_summary_id와 관련된 검색 결과만 보여주거나,
        # 혹은 다른 검색 조건에 따른 결과를 보여줄지 결정 필요.
        # 여기서는 다른 검색 조건이 있다면 그 결과도 보여주도록 함.
        if search_query_course_name or search_query_instructor_name or search_query_course_code:
            search_results_qs_for_list = review_service.get_reviews(
                course_name=search_query_course_name if search_query_course_name else None,
                course_code=search_query_course_code if search_query_course_code else None,
                inst_name=search_query_instructor_name if search_query_instructor_name else None
            )
            search_results = list(search_results_qs_for_list)
        elif selected_summary:  # summary_id로만 검색했고, 결과가 있다면 목록에 표시
            search_results = [selected_summary]

    # 2. summary_id가 없고, 다른 검색 파라미터가 있는 경우
    elif search_query_course_name or search_query_instructor_name or search_query_course_code:
        search_results_qs = review_service.get_reviews(
            course_name=search_query_course_name if search_query_course_name else None,
            course_code=search_query_course_code if search_query_course_code else None,
            inst_name=search_query_instructor_name if search_query_instructor_name else None
        )

        # 검색 결과가 정확히 하나인 경우, 해당 결과를 selected_summary로 바로 설정
        if search_results_qs.count() == 1:
            selected_summary = search_results_qs.first()
            if selected_summary:
                selected_summary_id = selected_summary.summary_id  # selected_summary_id 업데이트

        search_results = list(search_results_qs)  # 전체 검색 결과를 목록으로 사용

    context = {
        'search_query_course_name': search_query_course_name,
        'search_query_instructor_name': search_query_instructor_name,
        'search_query_course_code': search_query_course_code,
        'search_results': search_results,
        'selected_summary': selected_summary,
        'selected_summary_id': selected_summary_id,  # 템플릿에서 현재 선택된 ID를 알 수 있도록 전달
    }
    return render(request, 'home/review_search_page.html', context)