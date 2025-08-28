"""
대시보드 및 일반 뷰들
메인 대시보드, 마이페이지, 파일 업로드 등의 일반적인 페이지를 담당합니다.
"""

import os
import json
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from data_manager.models import *
from data_manager.services.graduation_engine import GraduationEngine
from ..services.gpt_service import extract_graduation_info_from_text
from ..services.graduation_file_service import save_graduation_data_to_db
from ..services.pdf_service import pdf_to_text
from ..utils import get_simplified_category_name


def index_view(request):
    """
    메인 인덱스 페이지
    로그인 여부를 판단하고, 로그인 페이지 혹은 대시보드 페이지로 이동
    """
    if request.user.is_authenticated:
        return render(request, 'home/dashboard.html')
    else:
        return render(request, 'home/index.html')


def course_serach_test_view(request):
    """강의 검색 테스트 페이지"""
    return render(request, 'home/search_test.html')


def dashboard_view(request):
    """대시보드 메인 페이지"""
    return render(request, 'home/dashboard.html')


def upload_pdf_view(request):
    """
    성적표 PDF 업로드 및 처리 뷰
    PDF를 텍스트로 변환하고 GPT로 파싱하여 졸업 정보를 DB에 저장
    """
    if request.method == "POST":
        pdf_file = request.FILES.get("graduation_pdf")
        if not pdf_file:
            return JsonResponse({"error": "파일이 업로드되지 않았습니다."}, status=400)
        
        # 파일 저장
        file_path = os.path.join(settings.BASE_DIR, "user_uploads", pdf_file.name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb+") as dest:
            for chunk in pdf_file.chunks():
                dest.write(chunk)
        
        # PDF 텍스트 변환 및 GPT 파싱
        text = pdf_to_text(file_path)
        parsed_data = extract_graduation_info_from_text(text)
        
        # DB 저장
        user_id = request.user.id if request.user.is_authenticated else 1
        record = save_graduation_data_to_db(parsed_data, user_id)
        
        return redirect('mypage')


def mypage_view(request):
    """
    마이페이지 뷰
    사용자의 학사 정보, 이수내역, 졸업엔진 결과 등을 표시
    """
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

    # 사용자 이수내역(Transcript)과 졸업엔진 결과(알림/요건) 제공
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