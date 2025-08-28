from rest_framework.views import APIView

from data_manager.models import *
from data_manager.serializers import CourseSerializer
from data_manager.services.course_filter_service import CourseFilterService
import json

from django.http import JsonResponse
from django.db.models import Min

from data_manager.services.review_service import ReviewService
from data_manager.serializers import CourseReviewSummarySerializer, UserReviewSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response 
from rest_framework import status 
from .models import CourseReviewSummary 
from .serializers import UserProfileSerializer
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes

def course_summary(request, course_id):
    """
    course_summ 테이블만 조회해 요약·그룹활동 여부만 반환
    """
    try:
        summ = CourseSumm.objects.get(course_id=course_id)
        data = {
            'course_summary':   summ.course_summarization,
            'group_activity':   summ.group_activity,   # 'Y' or 'N'
        }
    except CourseSumm.DoesNotExist:
        data = {
            'course_summary': '',
            'group_activity': 'N',
        }
    return JsonResponse(data)


class CourseSearchView(APIView):
    """
    예: /data-manager/course/search/?college_name=전자정보대학&dept_name=소프트웨어학부&instructor_name=김교수&credit=3&year=2023&term=1학기
    - unique=true 를 주면 course_code 기준으로 유일한 결과만 반환
    """

    def get(self, request):
        # 1) 쿼리 파라미터 추출
        college_name = request.query_params.get('college_name')
        dept_name = request.query_params.get('dept_name')
        category_id = request.query_params.get('category_id')

        instructor_name = request.query_params.get('instructor_name')
        course_name = request.query_params.get('course_name')

        category_root = request.query_params.get('category_root')
        category_child = request.query_params.get('category_child')
        category_grandchild = request.query_params.get('category_grandchild')

        # 학점 변환
        credit = request.query_params.get('credit')
        if credit is not None:
            try:
                credit = int(credit)
            except ValueError:
                return Response({"detail": "credit must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        # 학년도와 학기(term)는 문자열 그대로 전달 (서비스 내에서 처리)
        year = request.query_params.get('year')
        term = request.query_params.get('term')
        unique_flag = request.query_params.get('unique', 'false').lower() in ['1', 'true', 'yes']

        # 시간 제외 (exclude_day_time_map) JSON 파라미터 처리
        exclude_map_json = request.query_params.get('exclude_day_time_map')
        exclude_day_time_map = None
        if exclude_map_json:
            try:
                exclude_day_time_map = json.loads(exclude_map_json)
            except json.JSONDecodeError:
                return Response({"detail": "Invalid JSON for exclude_day_time_map"}, status=status.HTTP_400_BAD_REQUEST)

        # 2) Service 호출
        service = CourseFilterService()
        queryset = service.course_search(
            college_name=college_name,
            dept_name=dept_name,
            category_id=category_id,
            instructor_name=instructor_name,
            exclude_day_time_map=exclude_day_time_map,
            credit=credit,
            course_name=course_name,
            year=year,
            term=term
        )

        # 2) unique 옵션 처리: course_code 기준 대표 course_id만 선택 (MySQL 호환)
        if unique_flag:
            code_min_ids = queryset.values('course_code').annotate(repr_id=Min('course_id'))
            id_list = [row['repr_id'] for row in code_min_ids]
            queryset = Courses.objects.filter(course_id__in=id_list)

        # schedules 를 미리 가져오기
        queryset = queryset.prefetch_related('courseschedule_set')

        # 3) 직렬화 후 응답
        serializer = CourseSerializer(queryset, many=True)


        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def search_course_reviews(request):
    """
    강의명, 과목코드, 교수명을 통해 강의 리뷰 요약 정보를 검색합니다.
    GET 파라미터:
    - course_name (str, optional): 강의명 (부분 일치)
    - course_code (str, optional): 과목 코드 (정확히 일치)
    - instructor_name (str, optional): 교수명 (부분 일치)
    """
    course_name = request.query_params.get('course_name')
    course_code = request.query_params.get('course_code')
    instructor_name = request.query_params.get('instructor_name')

    service = ReviewService()
    queryset = service.get_reviews(
        course_name=course_name,
        course_code=course_code,
        inst_name=instructor_name
    )

    serializer = CourseReviewSummarySerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_user_reviews_for_summary(request, summary_id):
    """
    특정 강의 리뷰 요약(summary_id)에 해당하는 모든 사용자 리뷰를 가져옵니다.
    URL 경로 파라미터:
    - summary_id (int): CourseReviewSummary의 ID
    """
    service = ReviewService()
    try:
        # 먼저 CourseReviewSummary 객체가 실제로 존재하는지 확인합니다.
        summary_obj = CourseReviewSummary.objects.get(summary_id=summary_id)
    except CourseReviewSummary.DoesNotExist:
        return Response({"detail": "Review summary not found."}, status=status.HTTP_404_NOT_FOUND)

    queryset = service.get_user_reviews(summary_id=summary_obj.summary_id)

    serializer = UserReviewSerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def search_colleges(request):
    """
    대학 검색 API
    GET 파라미터:
    - q (str, optional): 대학명 부분 검색어
    """
    q = request.query_params.get('q', '').strip()
    return_all = request.query_params.get('all') == 'true'
    qs = College.objects.all()
    if q:
        qs = qs.filter(college_name__icontains=q)
    if not return_all:
        qs = qs.order_by('college_name')[:50]
    else:
        qs = qs.order_by('college_name')
    results = [
        {
            'id': c.college_id,
            'name': c.college_name,
        }
        for c in qs
    ]
    return Response({'results': results}, status=status.HTTP_200_OK)

@api_view(['GET'])
def search_departments(request):
    """
    학과(전공) 검색 API
    GET 파라미터:
    - q (str, optional): 학과명 부분 검색어
    - college_name (str, optional): 소속 단과대학명으로 필터링
    """
    q = request.query_params.get('q', '').strip()
    college_name = request.query_params.get('college_name', '').strip()
    return_all = request.query_params.get('all') == 'true'

    qs = Department.objects.select_related('college').all()
    if college_name:
        qs = qs.filter(college__college_name__iexact=college_name)
    if q:
        qs = qs.filter(dept_name__icontains=q)
    if not return_all:
        qs = qs.order_by('dept_name')[:100]
    else:
        qs = qs.order_by('dept_name')

    results = [
        {
            'id': d.dept_id,
            'name': d.dept_name,
            'college': d.college.college_name if d.college else None,
        }
        for d in qs
    ]
    return Response({'results': results}, status=status.HTTP_200_OK)

@api_view(['GET'])
def categories_flat(request):
    """
    카테고리 트리(평면 리스트) 제공 API
    각 항목: {category_id, category_name, parent_category_id}
    """
    qs = Category.objects.all().order_by('category_name')
    results = [
        {
            'category_id': c.category_id,
            'category_name': c.category_name,
            'parent_category_id': c.parent_category.category_id if c.parent_category else None,
        }
        for c in qs
    ]
    return Response({'results': results}, status=status.HTTP_200_OK)

@api_view(['GET'])
def categories_api(request):
    """모든 카테고리 정보를 JSON으로 반환합니다."""
    categories = list(
        Category.objects
                .all()
                .order_by('category_level', 'category_name')
                .values('category_id', 'category_name', 'parent_category_id', 'category_level')
    )
    return JsonResponse({'data': categories})

@api_view(['GET'])
def org_data_api(request):
    """단과대학, 학과, 전공 정보를 하나의 JSON으로 반환합니다."""
    colleges = list(
        College.objects
               .all()
               .order_by('college_name')
               .values('college_id', 'college_name')
    )
    departments = list(
        Department.objects
                  .all()
                  .order_by('dept_name')
                  .values('dept_id', 'dept_name', 'college_id')
    )
    majors = list(
        Major.objects
             .all()
             .order_by('major_name')
             .values('major_id', 'major_name', 'dept_id')
    )
    return JsonResponse({
        'colleges':    colleges,
        'departments': departments,
        'majors':      majors,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile_me(request):
    """
    현재 로그인 사용자의 UserProfile 정보를 반환합니다.
    필드 전체를 그대로 반환하며, null 가능 필드는 그대로 전달됩니다.
    """
    try:
        profile = request.user.userprofile
    except Exception:
        return Response({'detail': 'UserProfile not found'}, status=status.HTTP_404_NOT_FOUND)
    data = UserProfileSerializer(profile).data
    # 프론트 사용 편의를 위한 파생 필드 추가(문자열 이름들)
    data.update({
        'college_name': getattr(profile.college, 'college_name', None) if getattr(profile, 'college', None) else None,
        'department_name': getattr(profile.department, 'dept_name', None) if getattr(profile, 'department', None) else None,
        'ruleset_name': getattr(profile.rule_set, 'ruleset_name', None) if getattr(profile, 'rule_set', None) else None,
    })
    return Response(data, status=status.HTTP_200_OK)