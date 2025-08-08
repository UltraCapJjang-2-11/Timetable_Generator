# Views.py 리팩토링 가이드

## 📋 개요

기존 1,383줄의 `views.py` 파일을 기능별로 분리함

## 🔄 변경 사항

### 기존 구조
```
home/
├── views.py 
├── forms.py
├── services/
└── templates/
```

### 새로운 구조
```
home/
├── views.py (새로운 메인 파일 - import만 담당)
├── utils.py (공통 유틸리티 함수들)
├── views/
│   ├── __init__.py
│   ├── auth_views.py (인증 관련)
│   ├── chatbot_views.py (챗봇/자연어 처리 관련)
│   ├── timetable_views.py (시간표 생성/관리)
│   ├── review_views.py (리뷰 관련)
│   └── dashboard_views.py (대시보드/일반 페이지)
├── forms.py
├── services/
└── templates/
```

## 📁 파일별 상세 설명

### 1. `home/views.py` (메인 파일)
**역할**: 모든 뷰 함수들을 하나의 네임스페이스로 통합
**내용**:
- 각 모듈에서 뷰 함수들을 import
- 기존 URL 패턴과의 호환성 유지
- 하위 호환성을 위한 utils import

### 2. `home/utils.py` (공통 유틸리티)
**역할**: 여러 뷰에서 공통으로 사용되는 헬퍼 함수들
**포함 기능**:
- `get_effective_gen eral_category()`: 교양 카테고리 매핑
- `get_simplified_category_name()`: 카테고리 명칭 통일
- `apply_time_constraints()`: 시간 제약조건 적용
- `extract_number()`: 텍스트에서 숫자 추출
- `get_korean_day_abbr()`: 한글 요일 약자 변환
- `DummyObj`: CP-SAT 처리용 더미 객체

### 3. `home/views/auth_views.py` (인증 관련)
**역할**: 사용자 인증 및 세션 관리
**포함 뷰**:
- `CustomLoginView`: 사용자 로그인
- `signup()`: 회원가입
- `logout_view()`: 로그아웃

### 4. `home/views/chatbot_views.py` (챗봇 관련)
**역할**: Rasa 챗봇 연동 및 자연어 처리
**포함 뷰**:
- `parse_constraints()`: 자연어 텍스트 파싱
- `extract_constraints_from_rasa_response()`: Rasa 응답 처리
**주요 기능**:
- Rasa 서버와의 HTTP 통신
- 자연어에서 시간표 제약조건 추출
- 엔티티 매핑 및 변환

### 5. `home/views/timetable_views.py` (시간표 관련)
**역할**: 시간표 생성 알고리즘 및 관리
**포함 뷰**:
- `timetable_view()`: 시간표 생성 메인 페이지
- `generate_timetable_stream()`: 시간표 생성 알고리즘 (CP-SAT 사용)
- `manage_view()`: 저장된 시간표 관리 페이지
- `save_timetable()`: 시간표 저장 API
- `delete_timetable()`: 시간표 삭제 API

**주요 기능**:
- CP-SAT 제약 만족 알고리즘 적용
- 시간 충돌 검사
- 학점 및 카테고리 제약 조건 처리
- 2-Phase 최적화 (Phase 1: 최적값 찾기, Phase 2: 모든 해 찾기)

### 6. `home/views/review_views.py` (리뷰 관련)
**역할**: 강의 리뷰 검색 및 조회
**포함 뷰**:
- `review_detail_page()`: 리뷰 상세 페이지
- `review_search_summary_view()`: 리뷰 검색 및 요약

### 7. `home/views/dashboard_views.py` (대시보드 관련)
**역할**: 메인 대시보드 및 일반 페이지들
**포함 뷰**:
- `index_view()`: 메인 인덱스 페이지
- `dashboard_view()`: 대시보드 메인
- `mypage_view()`: 마이페이지 (졸업 정보 표시)
- `upload_pdf_view()`: 성적표 PDF 업로드
- `course_serach_test_view()`: 강의 검색 테스트

## 🚀 시간표 생성 알고리즘 설명

### 개요
시간표 생성은 제약 만족 문제(Constraint Satisfaction Problem)로 Google OR-Tools의 CP-SAT 솔버를 사용합니다.

### 주요 제약 조건
1. **학점 제약**: 총 학점, 전공 학점, 교양 학점
2. **시간 충돌**: 같은 시간대에 여러 강의 불가
3. **공강 요일**: 사용자 지정 공강 요일
4. **강의 중복**: 같은 강의명의 다른 분반 중복 불가
5. **시간대 제약**: 특정 시간대 선호/회피

### 2-Phase 최적화 과정
1. **Phase 1**: 전공필수 우선 + 동일학년 전공선택 우선으로 최적값 계산
2. **Phase 2**: Phase 1의 최적값을 강제하고 모든 가능한 해 탐색

### 알고리즘 흐름
```python
1. 사용자 제약조건 파싱
2. 후보 강의 목록 생성
3. 필터링 (학년, 학과, 시간, 공강 등)
4. CP-SAT 모델 구성
5. Phase 1: 최적값 계산
6. Phase 2: 모든 해 탐색
7. 결과 반환 (최대 50개)
```

## 🔧 개발 가이드

### 새로운 뷰 추가하기
1. 적절한 모듈 파일 선택 (또는 새로 생성)
2. 뷰 함수 구현
3. `home/views/__init__.py`에 import 추가
4. 메인 `views.py`에 import 추가 (필요시)

### 공통 기능 추가하기
1. `utils.py`에 함수 추가
2. 해당 뷰 모듈에서 import하여 사용

### 디버깅 팁
- 각 모듈별로 독립적인 디버깅 가능
- 시간표 생성 시 `DEBUG:` 로그 활용
- CP-SAT 솔버 상태 확인

## 📊 성능 개선 사항

### 코드 구조
- **가독성**: 기능별 분리로 코드 이해도 향상
- **유지보수성**: 각 모듈별 독립적 수정 가능
- **테스트 용이성**: 모듈별 단위 테스트 가능

### 시간표 생성 최적화
- **필터링 최적화**: 후보 강의 사전 필터링으로 계산량 감소
- **메모리 효율성**: 불필요한 데이터 제거
- **병렬 처리**: 다중 해 탐색 시 효율적인 콜백 사용

## 🚨 주의사항

### 기존 코드 호환성
- 모든 기존 URL 패턴 유지
- 기존 템플릿 코드 수정 불필요
- 기존 JavaScript 코드 영향 없음

### 개발 시 주의점
1. **Import 순서**: 순환 import 방지
2. **상대 import**: 모듈 내에서 `..utils` 형태로 import
3. **네이밍**: 기존 함수명 유지

## 📚 참고 자료

### 사용된 라이브러리
- **Django**: 웹 프레임워크
- **OR-Tools**: 제약 만족 문제 해결
- **Rasa**: 자연어 처리 챗봇
- **JSON**: 데이터 직렬화

### 알고리즘 참고
- CP-SAT (Constraint Programming - Satisfiability)
- 제약 만족 문제 (CSP)
- 정수 선형 계획법 (ILP)

## 🔄 마이그레이션 체크리스트

- [x] 기존 views.py 백업
- [x] 기능별 모듈 분리 완료
- [x] Import 구조 정리
- [x] 공통 유틸리티 분리
- [x] 문서화 완료
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 실행
- [ ] 성능 벤치마크 확인

## 🤝 팀원 가이드

### 코드 리뷰 시 확인사항
1. 적절한 모듈에 코드가 위치하는가?
2. 공통 기능은 utils.py에 분리되었는가?
3. 함수 네이밍이 일관성 있는가?
4. 적절한 docstring이 작성되었는가?

### 버그 발생 시 대응
1. 해당 기능의 모듈 파일 확인
2. 관련 utils 함수 확인
3. 디버그 로그 확인
4. 단위 테스트 실행

---

**작성일**: 2024년 12월
**작성자**: 개발팀
**버전**: 1.0 