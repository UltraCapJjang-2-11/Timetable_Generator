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