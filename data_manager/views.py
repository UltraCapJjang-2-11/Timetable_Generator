# data_manager/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from data_manager.models import Courses, CourseSumm
from data_manager.serializers import CourseSerializer
from data_manager.services.course_filter_service import CourseFilterService
import json

from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404

from data_manager.services.review_service import ReviewService
from data_manager.serializers import CourseReviewSummarySerializer, UserReviewSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response 
from rest_framework import status 
from .models import CourseReviewSummary 

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
