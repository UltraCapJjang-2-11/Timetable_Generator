import json
import os
import uuid

from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.core.exceptions import ValidationError

from data_manager.models import UserProfile
from data_manager.models import TranscriptFile, Courses, Semester, Transcript

from onboarding.pdf_processing import pdf_validation_check, extract_to_dict, parsing_to_json, pdf_visualization
from data_manager.services.user_profile_service import UserProfileService
from data_manager.services.graduation_engine import GraduationEngine
from data_manager.services.graduation_types import RuleResult

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from django.conf import settings


def onboarding(request):
    return render(request, 'onboarding/onboarding.html')

class UserRegistrationView(View):
    @transaction.atomic
    def post(self, request):

        try:
            data = json.loads(request.body)
            email = data.get('email', '').strip()
            password = data.get('password', '')

            # 빈 값 검사
            if not email or not password:
                return JsonResponse({
                    'status': 'error', 'field': 'all',
                    'message': '이메일과 비밀번호를 모두 입력해주세요.'
                }, status=400)

            # 이메일 중복 검사
            if User.objects.filter(email__iexact=email).exists():
                return JsonResponse({
                    'status': 'error', 'field': 'email',
                    'message': '이미 사용 중인 이메일입니다.'
                }, status=409)

            # 비밀번호 강도 검사 (Django 기본 검증 사용)
            try:
                validate_password(password)
            except ValidationError as e:
                print(e.messages)
                return JsonResponse({
                    'status': 'error', 'field': 'password',
                    'message': list(e.messages) # 첫 번째 오류 메시지를 전달
                }, status=400)

            # 모든 검증 통과 시 사용자 생성
            user = User.objects.create_user(username=email, email=email, password=password)
            user.is_active = True
            user.save()

            UserProfile.objects.create(user=user)
            login(request, user)

            return JsonResponse({'status': 'success', 'message': '계정이 생성되었으며, 자동으로 로그인되었습니다.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': '알 수 없는 오류가 발생했습니다.'}, status=500)

@method_decorator(login_required, name='dispatch')
class ProcessPdfView(View):
    def post(self, request):
        if not request.FILES.get('pdf_file'):
            return JsonResponse({'status': 'error', 'message': '파일이 전달되지 않았습니다.'}, status=400)

        pdf_file = request.FILES['pdf_file']
        user_profile = request.user.userprofile

        # --- 1. 파일 검증 ---
        # 파일을 임시 경로에 저장하여 검증 함수에 전달
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_pdf_path = os.path.join(temp_dir, f"{uuid.uuid4()}.pdf")
        with open(temp_pdf_path, 'wb+') as destination:
            for chunk in pdf_file.chunks():
                destination.write(chunk)

        if not pdf_validation_check.validate_pdf_format(temp_pdf_path):
            os.remove(temp_pdf_path)  # 임시 파일 삭제
            return JsonResponse({'status': 'error', 'message': '지원하지 않는 형식의 성적 증명서입니다.'}, status=400)

        # --- 2. 데이터 추출 및 파싱 ---
        raw_data = extract_to_dict.identify_document_objects(temp_pdf_path)
        parsed_data = parsing_to_json.create_json_from_identified_objects(raw_data)

        # --- 2-1. 파싱된 이수내역을 DB Courses 기준으로 정합성 필터링 및 pk 부여 ---
        matched_course_items = []
        course_history = parsed_data.get('학점이수현황') or []

        for row in course_history:
            try:
                year = int(str(row.get('년도', '')).strip()) if row.get('년도') not in (None, '') else None
            except Exception:
                year = None
            term = str(row.get('학기', '')).strip() or None

            # 교과목번호는 문자열로 변환하여 매칭 시도
            code_val = row.get('교과목번호')
            course_code = str(code_val).strip() if code_val not in (None, '') else None

            if not (year and term and course_code):
                print(f"[ProcessPdfView] Skip row due to missing keys: year={year}, term={term}, code={course_code}")
                continue

            semester_obj = Semester.objects.filter(year=year, term=term).first()
            if not semester_obj:
                print(f"[ProcessPdfView] Semester not found: {year} {term}")
                continue

            # 우선 정확 일치로 조회
            course_obj = Courses.objects.filter(course_code=course_code, semester=semester_obj).first()
            if not course_obj:
                # 보수적으로 부분 일치 보조(디버그 용도)
                course_obj = Courses.objects.filter(course_code__icontains=course_code, semester=semester_obj).first()

            if not course_obj:
                print(f"[ProcessPdfView] Course not found for code={course_code}, semester={year} {term}")
                continue

            matched_course_items.append({
                'id': course_obj.pk,
                '년도': year,
                '학기': term,
                '교과목번호': course_code,
                '교과목명': row.get('교과목명'),
                '학점': row.get('학점'),
                '이수구분': row.get('이수구분'),
                '성적': row.get('성적'),
            })

        # UI에서 사용하는 이수내역을 필터링된 정규화 리스트로 대체
        parsed_data['학점이수현황'] = matched_course_items

        # --- 3. 이미지 생성 ---
        output_dir = os.path.join(settings.MEDIA_ROOT, 'transcripts', str(user_profile.pk))
        os.makedirs(output_dir, exist_ok=True)
        # generate_visual_reports가 생성된 파일 경로 딕셔너리를 반환한다고 가정
        image_paths = pdf_visualization.generate_visual_reports(
            file_path=temp_pdf_path,
            identified_objects=raw_data,
            output_dir=output_dir
        )

        # --- 4. DB 기록 ---
        # 기존 기록이 있다면 삭제
        TranscriptFile.objects.filter(user_profile=user_profile).delete()

        # FileField에 저장하기 위해 파일을 다시 열어야 할 수 있음
        pdf_file.seek(0)

        record = TranscriptFile.objects.create(
            user_profile=user_profile,
            original_filename=pdf_file.name,
            pdf_file=pdf_file,
            original_images=image_paths.get('original_pages', []),
            student_info_image=image_paths.get('student_info'),
            course_history_image=image_paths.get('course_history'),
            credit_summary_image=image_paths.get('credit_summary'),
            parsed_data=parsed_data
        )

        os.remove(temp_pdf_path)  # 임시 파일 삭제

        # --- 5. 최종 응답 ---
        # 프론트엔드에서 사용할 수 있도록 전체 경로를 URL로 변환
        def path_to_url(path):
            if not path:
                return None
            # 절대 경로를 상대 경로로 변환
            relative_path = os.path.relpath(path, settings.MEDIA_ROOT)
            # Windows 경로 구분자를 웹 URL용으로 변환
            relative_path = relative_path.replace('\\', '/')
            return settings.MEDIA_URL + relative_path
        
        response_data = {
            'status': 'success',
            'parsed_data': record.parsed_data,
            'image_urls': {
                'original': [path_to_url(p) for p in record.original_images],
                'student_info': path_to_url(record.student_info_image),
                'course_history': path_to_url(record.course_history_image),
            }
        }
        return JsonResponse(response_data)

@method_decorator(login_required, name='dispatch')
class SaveAcademicInfoView(View):
    def post(self, request):
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'status': 'error', 'message': '잘못된 요청 본문입니다.'}, status=400)

        college_name = (payload.get('college') or '').strip() or None
        department_name = (payload.get('department') or '').strip() or None
        student_id = (payload.get('student_id') or '').strip()  # 현재 저장 대상 아님(확장 여지)
        user_name = (payload.get('name') or '').strip()              # 현재 저장 대상 아님(확장 여지)
        admission_year = payload.get('curriculum_year')
        current_grade = payload.get('year')
        completed_semesters = payload.get('completed_semesters')

        # 타입 캐스팅(숫자 문자열 -> int)
        def to_int_or_none(v):
            try:
                if v is None or v == '':
                    return None
                return int(v)
            except Exception:
                return None

        admission_year = to_int_or_none(admission_year)
        current_grade = to_int_or_none(current_grade)
        completed_semesters = to_int_or_none(completed_semesters)

        svc = UserProfileService()
        user_profile = request.user.userprofile

        updated_profile, ruleset = svc.update_academic_info(
            user_profile,
            user_name=user_name,
            user_student_id=student_id,
            college_name=college_name,
            department_name=department_name,
            admission_year=admission_year,
            current_grade=current_grade,
            completed_semesters=completed_semesters,
        )

        return JsonResponse({
            'status': 'success',
            'ruleset_id': getattr(ruleset, 'ruleset_id', None),
        })

@method_decorator(login_required, name='dispatch')
class SaveTranscriptsView(View):
    def post(self, request):
        try:
            payload = json.loads(request.body.decode('utf-8'))
            print(payload)
        except Exception as e:
            print(e)
            return JsonResponse({'status': 'error', 'message': '잘못된 요청 본문입니다.'}, status=400)

        items = payload.get('courses') or []
        if not isinstance(items, list):
            return JsonResponse({'status': 'error', 'message': 'courses 형식이 올바르지 않습니다.'}, status=400)

        user_profile = request.user.userprofile
        saved, updated = 0, 0

        for item in items:
            # 1) 우선 course_id로 조회
            course_id = item.get('course_id') or item.get('id')
            grade = item.get('grade') or item.get('성적')

            course = None
            if course_id:
                course = Courses.objects.filter(pk=course_id).first()

            # 2) 폴백: (year, term, course_code)로 대표 분반 해석
            if not course:
                year = item.get('year') or item.get('년도')
                term = item.get('term') or item.get('학기')
                code = item.get('course_code') or item.get('교과목번호')
                try:
                    year = int(str(year).strip()) if year not in (None, '') else None
                except Exception:
                    year = None
                term = str(term).strip() if term not in (None, '') else None
                code = str(code).strip() if code not in (None, '') else None
                if year and term and code:
                    sem = Semester.objects.filter(year=year, term=term).first()
                    if sem:
                        # 대표 분반(최소 course_id)을 기본으로 채택
                        course = Courses.objects.filter(course_code=code, semester=sem).order_by('course_id').first()

            if not course:
                print(f"[SaveTranscriptsView] Course resolve failed: payload={item}")
                continue

            # upsert by unique (user_profile, course)
            obj, created = Transcript.objects.update_or_create(
                user_profile=user_profile,
                course=course,
                defaults={'grade': grade or ''},
            )
            if created:
                saved += 1
            else:
                updated += 1

        return JsonResponse({'status': 'success', 'saved': saved, 'updated': updated})

@method_decorator(login_required, name='dispatch')
class EvaluateGraduationView(View):
    def get(self, request):
        user_profile = request.user.userprofile
        # 사용자 이수내역 조회 (관련 FK 함께)
        transcripts = (
            Transcript.objects
            .filter(user_profile=user_profile)
            .select_related('course', 'course__category', 'course__category__parent_category')
        )

        engine = GraduationEngine(user_profile, transcripts)
        results = engine.run()

        # 규칙셋의 카테고리 트리 수집
        categories_set = {}
        required_by_category = {}
        if user_profile.rule_set:
            rules_qs = user_profile.rule_set.rules.select_related('category', 'category__parent_category').all()
            for rule in rules_qs:
                cat = rule.category
                # 하위 -> 상위로 조상까지 모두 등록
                cur = cat
                while cur:
                    categories_set[cur.category_id] = cur
                    cur = cur.parent_category
                # 동일 카테고리에 여러 룰이 있을 경우, 더 큰 요구치 우선
                prev = required_by_category.get(cat.category_id)
                required_by_category[cat.category_id] = max(prev or 0, rule.min_credits or 0)

        # 카테고리 노드 직렬화
        def serialize_cat(cat_obj):
            return {
                'category_id': cat_obj.category_id,
                'category_name': cat_obj.category_name,
                'parent_category_id': cat_obj.parent_category.category_id if cat_obj.parent_category else None,
            }

        categories = [serialize_cat(c) for c in categories_set.values()]

        # 카테고리별 이수 학점(엔진 전처리 결과 사용: 조상 계층까지 누적됨)
        earned_map = {}
        credits_by_category = engine.processed_data.get('credits_by_category', {})
        for cid in categories_set.keys():
            earned_map[cid] = float(credits_by_category.get(cid, 0.0))

        # RuleResult 직렬화
        results_json = RuleResult.list_to_dicts(results)
        # 부족 항목 목록(remark)
        lacking = [r['remark'] for r in results_json if (not r.get('is_satisfied')) and r.get('remark')]

        payload = {
            'status': 'success',
            'effective_year': engine.effective_year,
            'ruleset_name': getattr(user_profile.rule_set, 'ruleset_name', None) if getattr(user_profile, 'rule_set', None) else None,
            'categories': categories,
            'required_by_category': required_by_category,
            'earned_by_category': earned_map,
            'results': results_json,
            'lacking': lacking,
        }
        return JsonResponse(payload)