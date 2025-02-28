# data_manager/urls.py

from django.urls import path
from data_manager.views import CourseSearchView

urlpatterns = [
    # 예: /data-manager/course/search/
    path('course/search/', CourseSearchView.as_view(), name='course-search'),
]
