from django.urls import path
from .views import *
from . import views
from data_manager.views import CourseSearchView
urlpatterns = [
    path('', index_view, name='index'), # 기본 페이지 : 로그인 세션 확인
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('signup/', signup, name='signup'),

    path('dashboard/', dashboard_view, name='dashboard'),  # 로그인 후 이동할 대시보드

    path('upload_graduation/', upload_pdf_view, name='upload_graduation'),
    path('mypage/', mypage_view, name='mypage'),

    path('timetable/', timetable_view, name='timetable'),  # 시간표 페이지
    path('generate_timetable_stream/', generate_timetable_stream, name='generate_timetable_stream'),
    path("parse_constraints/", parse_constraints, name="parse_constraints"),
    path('manage/', views.manage_view, name='manage'),
    path('search_test/', course_serach_test_view, name='search_test'),
    
    # 시간표 저장/삭제 API
    path('save_timetable/', save_timetable, name='save_timetable'),
    path('delete_timetable/<int:timetable_id>/', delete_timetable, name='delete_timetable'),

    path('course/search/', CourseSearchView.as_view(), name='course-search'),
    path('reviews/', review_search_summary_view, name='review_search_page'),
    path('reviews/<int:summary_id>/', review_detail_page, name='review-detail-page'),
]