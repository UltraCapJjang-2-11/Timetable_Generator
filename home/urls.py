from django.urls import path
from .views import login_view, dashboard_view, timetable_view

urlpatterns = [
    path('', login_view, name='login'),  # 기본 페이지 = 로그인
    path('dashboard/', dashboard_view, name='dashboard'),  # 로그인 후 이동할 대시보드
    path('timetable/', timetable_view, name='timetable'),  # 로그인 후 이동할 대시보드
]