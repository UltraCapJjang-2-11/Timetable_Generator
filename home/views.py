"""
메인 views.py 파일 - 기존 뷰들을 새로운 구조로 리팩토링함

이 파일은 기존 views.py를 대체하며, 각 기능별로 분리된 뷰 모듈들을 import하여 사용합니다.
- 인증 관련: views.auth_views
- 챗봇 관련: views.chatbot_views  
- 시간표 관련: views.timetable_views
- 리뷰 관련: views.review_views
- 대시보드 관련: views.dashboard_views
- 공통 유틸리티: utils.py
"""

# 기존 뷰들을 새로운 구조로 import
from .views.auth_views import CustomLoginView, signup, logout_view
from .views.chatbot_views import parse_constraints, extract_constraints_from_rasa_response
from .views.timetable_views import (
    timetable_view, generate_timetable_stream, 
    manage_view, save_timetable, delete_timetable
)
from .views.review_views import review_detail_page, review_search_summary_view
from .views.dashboard_views import (
    index_view, course_serach_test_view, dashboard_view, 
    upload_pdf_view, mypage_view
)
from .views.chat_views import get_chat_history

# 하위 호환성을 위해 기존 import 유지
from .utils import *

# 뷰 함수들은 이제 각각의 모듈에서 import됩니다.
# 이전에 이 파일에 직접 정의되어 있던 모든 함수들이 각각의 모듈로 이동되었습니다.