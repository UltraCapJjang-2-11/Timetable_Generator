from django.urls import path
from .views import login_view, dashboard_view, timetable_view, generate_timetable, course_serach_test_view

urlpatterns = [
    path('', login_view, name='login'),  # 기본 페이지 = 로그인
    path('dashboard/', dashboard_view, name='dashboard'),  # 로그인 후 이동할 대시보드
    path('timetable/', timetable_view, name='timetable'),  # 시간표 페이지
    path('generate_timetable/', generate_timetable, name='generate_timetable'),  # 시간표 생성 API
    path('search_test/', course_serach_test_view, name='search_test'),
]