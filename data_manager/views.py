# data_manager/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from data_manager.serializers import CourseSerializer
from data_manager.course.course_filter_service import CourseFilterService
import json


class CourseSearchView(APIView):
    """
    예: /data-manager/course/search/?dept_name=소프트웨어학부&instructor_name=김교수&credit=3&year=2023&term=1학기
    """

    def get(self, request):
        # 1) 쿼리 파라미터 추출
        dept_name = request.query_params.get('dept_name')
        category_name = request.query_params.get('category_name')
        instructor_name = request.query_params.get('instructor_name')
        course_name = request.query_params.get('course_name')

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
        queryset = service.get_final_results(
            dept_name=dept_name,
            category_name=category_name,
            instructor_name=instructor_name,
            exclude_day_time_map=exclude_day_time_map,
            credit=credit,
            course_name=course_name,
            year=year,
            term=term
        )

        # 3) 직렬화 후 응답
        serializer = CourseSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
