# 빠른 참조 가이드 (Quick Reference)

## 🎯 어떤 파일을 수정해야 할까?

### 인증 관련 수정 시
```python
# 파일: home/views/auth_views.py
def signup(request):
    # 회원가입 로직 수정
    pass

def logout_view(request):
    # 로그아웃 로직 수정
    pass
```

### 시간표 생성 알고리즘 수정 시
```python
# 파일: home/views/timetable_views.py
def generate_timetable_stream(request):
    # 시간표 생성 로직 수정
    # CP-SAT 알고리즘 파라미터 조정
    pass
```

### 챗봇 응답 처리 수정 시
```python
# 파일: home/views/chatbot_views.py
def parse_constraints(request):
    # Rasa 서버 통신 로직 수정
    pass
```

### 공통 유틸리티 함수 수정 시
```python
# 파일: home/utils.py
def get_effective_general_category(course):
    # 교양 카테고리 매핑 로직 수정
    pass
```

## 🔧 새로운 뷰 추가하기

### 1. 기존 모듈에 추가
```python
# 예: home/views/dashboard_views.py
def new_dashboard_feature(request):
    """새로운 대시보드 기능"""
    # 새로운 기능 구현
    return render(request, 'template.html')
```

### 2. 새로운 모듈 생성
```python
# 새 파일: home/views/new_feature_views.py
"""새로운 기능 관련 뷰들"""

def new_feature_view(request):
    """새로운 기능 메인 뷰"""
    return render(request, 'new_feature.html')
```

### 3. Import 추가
```python
# home/views/__init__.py에 추가
from .new_feature_views import *

# home/views.py에 추가
from .views.new_feature_views import new_feature_view
```

## 🐛 디버깅 가이드

### 시간표 생성 오류 시
```python
# 로그 확인 지점
print("DEBUG: --- Timetable Generation Start ---")
print("DEBUG: candidates count =", len(candidates))
print("DEBUG: CP-SAT status =", status)
```

### 챗봇 연동 오류 시
```python
# Rasa 서버 연결 확인
try:
    rasa_response = requests.post(RASA_WEBHOOK_ENDPOINT, json=data)
    if rasa_response.status_code != 200:
        print('Rasa 서버 응답 오류:', rasa_response.status_code)
except Exception as e:
    print('Rasa 서버 연결 오류:', str(e))
```

## 📂 파일 구조 매핑

| 기능 | 파일 위치 | 주요 함수 |
|------|-----------|-----------|
| 로그인/회원가입 | `views/auth_views.py` | `signup`, `logout_view` |
| 시간표 생성 | `views/timetable_views.py` | `generate_timetable_stream` |
| 시간표 저장/삭제 | `views/timetable_views.py` | `save_timetable`, `delete_timetable` |
| 챗봇 파싱 | `views/chatbot_views.py` | `parse_constraints` |
| 리뷰 검색 | `views/review_views.py` | `review_search_summary_view` |
| 대시보드 | `views/dashboard_views.py` | `dashboard_view`, `mypage_view` |
| 공통 유틸리티 | `utils.py` | `get_effective_general_category` 등 |

## 🚀 자주 사용하는 코드 스니펫

### 1. 새로운 API 뷰 추가
```python
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@csrf_exempt
def new_api_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # 처리 로직
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=405)
```

### 2. 학생 정보 가져오기
```python
def get_student_info(request):
    user_id = request.user.id if request.user.is_authenticated else 1
    grad_record = GraduationRecord.objects.filter(user_id=user_id).last()
    
    if grad_record:
        return {
            'major': grad_record.user_major,
            'year': grad_record.user_year,
            'completed_courses': json.loads(grad_record.completed_courses or '[]')
        }
    return None
```

### 3. 강의 검색 및 필터링
```python
from data_manager.course.course_filter_service import CourseFilterService

def search_courses(year=2025, term='1학기', category='전공'):
    svc = CourseFilterService()
    courses = svc.course_search(
        year=year, 
        term=term, 
        category_name=category
    ).order_by('course_name')
    return courses
```

## 🔄 마이그레이션 후 확인사항

### 1. URL 패턴 확인
```python
# urls.py에서 import 확인
from home.views import timetable_view, generate_timetable_stream
# 또는
from home.views.timetable_views import timetable_view, generate_timetable_stream
```

### 2. 템플릿에서 뷰 호출 확인
```html
<!-- 기존 방식 그대로 사용 가능 -->
<form action="{% url 'generate_timetable_stream' %}" method="get">
    <!-- 폼 내용 -->
</form>
```

### 3. JavaScript에서 API 호출 확인
```javascript
// 기존 API 엔드포인트 그대로 사용 가능
fetch('/api/save_timetable/', {
    method: 'POST',
    body: JSON.stringify(data),
    headers: {'Content-Type': 'application/json'}
})
```

## ⚠️ 주의사항

### Import 순서
```python
# 올바른 순서
from django.shortcuts import render
from django.http import JsonResponse
from ..utils import get_effective_general_category
from data_manager.models import *

# 잘못된 순서 (순환 import 위험)
from ..utils import *
from .other_views import some_function  # 위험!
```

### 상대 Import 사용
```python
# 모듈 내에서 utils 사용 시
from ..utils import get_effective_general_category

# 같은 패키지 내 다른 모듈 사용 시
from .auth_views import CustomLoginView
```

## 🆘 문제 해결

### 1. Import 오류 시
```bash
# 오류: ModuleNotFoundError
# 해결: Python 경로 확인 및 __init__.py 확인
```

### 2. 뷰 함수 찾을 수 없음
```python
# 오류: 'module' object has no attribute 'view_name'
# 해결: views/__init__.py에 해당 함수 import 추가
```

### 3. 순환 Import 오류
```python
# 오류: ImportError: cannot import name 'X' from partially initialized module
# 해결: Import 순서 조정 또는 지연 import 사용
```

---