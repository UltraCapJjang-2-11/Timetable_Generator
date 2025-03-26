from django.urls import path
from .views import login_view, dashboard_view, timetable_view, generate_timetable_stream, upload_pdf_view
from . import views

urlpatterns = [
    path('', login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('timetable/', timetable_view, name='timetable'),
    path('generate_timetable_stream/', generate_timetable_stream, name='generate_timetable_stream'),
    path('upload_graduation/', upload_pdf_view, name='upload_graduation'),
    # 마이페이지: /mypage/ → mypage_view
    path('mypage/', views.mypage_view, name='mypage'),

   
]
