# data_manager/urls.py

from django.urls import path

import data_manager.views
from data_manager.views import *

urlpatterns = [
    path('course/<int:course_id>/summary/', course_summary, name='course-summary'),
    path('reviews/summary/<int:summary_id>/', get_user_reviews_for_summary, name='get-user-reviews-for-summary'),
    path('search/colleges/', search_colleges, name='search-colleges'),
    path('search/departments/', search_departments, name='search-departments'),
    path('categories/flat/', categories_flat, name='categories-flat'),
    path('api/categories/', categories_api, name='api_categories'),
    path('api/org-data/', org_data_api, name='api_org_data'),
    path('api/user-profile/me/', user_profile_me, name='api_user_profile_me'),
]
