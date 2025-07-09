"""
대시보드 및 일반 뷰들
메인 대시보드, 마이페이지, 파일 업로드 등의 일반적인 페이지를 담당합니다.
"""

import os
import json
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from data_manager.models import GraduationRecord
from ..services.gpt_service import extract_graduation_info_from_text
from ..services.graduation_file_service import save_graduation_data_to_db
from ..services.pdf_service import pdf_to_text


def index_view(request):
    """
    메인 인덱스 페이지
    로그인 여부를 판단하고, 로그인 페이지 혹은 대시보드 페이지로 이동
    """
    if request.user.is_authenticated:
        return render(request, 'home/dashboard.html')
    else:
        return redirect('/login')


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
    사용자의 졸업 정보, 이수 내역, 부족한 과목 등을 표시
    """
    user_id = request.user.id if request.user.is_authenticated else 1
    record = GraduationRecord.objects.filter(user_id=user_id).last()
    context = {}
    
    if record:
        # 기본 정보 설정
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
        
        # JSON 데이터 파싱
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
        
        # 미이수 과목 정보 처리
        try:
            missing_subjects = json.loads(record.missing_major_subjects or '[]')
            context['missing_subjects'] = missing_subjects if isinstance(missing_subjects, list) else []
            
            # missing_subjects를 alerts로 변환
            alerts = []
            for item in context['missing_subjects']:
                if isinstance(item, dict) and 'type' in item and 'description' in item:
                    alerts.append(f"{item['type']}: {item['description']}")
            context['alerts'] = alerts
        except:
            context['missing_subjects'] = []
            context['alerts'] = []
        
        # 기타 정보 파싱
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
        # 기본값 설정 (졸업 정보가 없는 경우)
        context.update({
            'user_student_id': "", 'user_name': "", 'user_major': "", 'user_year': "",
            'total_credits': 0, 'major_credits': 0, 'general_credits': 0, 'free_credits': 0,
            'total_requirement': 0, 'major_requirement_data': {}, 'free_requirement': 0,
            'missing_total': 0, 'missing_major': 0, 'missing_major_essential': 0,
            'missing_major_elective': 0, 'missing_general': 0, 'missing_free': 0,
            'missing_subjects': [], 'completed_courses': [], 'missing_general_sub': {},
            'detailed_credits': {}, 'general_requirement': {}, 'alerts': [],
            'error_message': "졸업 정보를 찾을 수 없습니다. 성적표 PDF를 업로드해주세요."
        })
    
    return render(request, 'home/mypage.html', context) 