# data_manager/urls.py

from django.urls import path

import data_manager.views
from data_manager.views import CourseSearchView, course_summary, search_course_reviews, get_user_reviews_for_summary

urlpatterns = [
    path('course/<int:course_id>/summary/', course_summary, name='course-summary'),
    path('reviews/summary/<int:summary_id>/', get_user_reviews_for_summary, name='get-user-reviews-for-summary'),
]
