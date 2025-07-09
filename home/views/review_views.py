"""
리뷰 관련 뷰들
강의 리뷰 검색, 조회, 상세보기 등을 담당합니다.
"""

from django.shortcuts import render
from data_manager.services.review_service import ReviewService


def review_detail_page(request, summary_id):
    """
    특정 강의 리뷰 요약에 대한 사용자 코멘트 페이지를 렌더링합니다.
    
    Args:
        request: HTTP 요청 객체
        summary_id: 리뷰 요약 ID
        
    Returns:
        렌더링된 리뷰 상세 페이지
    """
    # summary_id를 템플릿으로 전달하여 JS에서 사용할 수 있도록 합니다.
    # 실제 데이터 로딩은 JS에서 API를 통해 이루어집니다.
    return render(request, 'home/review_detail_page.html', {'summary_id_from_view': summary_id})


def review_search_summary_view(request):
    """
    리뷰 검색 및 요약 정보를 보여주는 뷰
    강의명, 교수명, 강의코드로 리뷰를 검색할 수 있습니다.
    """
    # 검색 파라미터 추출
    search_query_course_name = request.GET.get('course_name', '')
    search_query_instructor_name = request.GET.get('instructor_name', '')
    search_query_course_code = request.GET.get('course_code', '')
    selected_summary_id = request.GET.get('summary_id')

    search_results = []
    selected_summary = None

    review_service = ReviewService()

    # 1. summary_id가 직접 제공된 경우, 우선적으로 해당 요약 정보 로드
    if selected_summary_id:
        summary_queryset = review_service.get_reviews(summary_id=selected_summary_id)
        selected_summary = summary_queryset.first()
        # 이 경우, 다른 검색 조건이 있더라도 selected_summary_id를 우선하므로,
        # search_results는 selected_summary_id와 관련된 검색 결과만 보여주거나,
        # 혹은 다른 검색 조건에 따른 결과를 보여줄지 결정 필요.
        # 여기서는 다른 검색 조건이 있다면 그 결과도 보여주도록 함.
        if search_query_course_name or search_query_instructor_name or search_query_course_code:
            search_results_qs_for_list = review_service.get_reviews(
                course_name=search_query_course_name if search_query_course_name else None,
                course_code=search_query_course_code if search_query_course_code else None,
                inst_name=search_query_instructor_name if search_query_instructor_name else None
            )
            search_results = list(search_results_qs_for_list)
        elif selected_summary:  # summary_id로만 검색했고, 결과가 있다면 목록에 표시
            search_results = [selected_summary]

    # 2. summary_id가 없고, 다른 검색 파라미터가 있는 경우
    elif search_query_course_name or search_query_instructor_name or search_query_course_code:
        search_results_qs = review_service.get_reviews(
            course_name=search_query_course_name if search_query_course_name else None,
            course_code=search_query_course_code if search_query_course_code else None,
            inst_name=search_query_instructor_name if search_query_instructor_name else None
        )

        # 검색 결과가 정확히 하나인 경우, 해당 결과를 selected_summary로 바로 설정
        if search_results_qs.count() == 1:
            selected_summary = search_results_qs.first()
            if selected_summary:
                selected_summary_id = selected_summary.summary_id  # selected_summary_id 업데이트

        search_results = list(search_results_qs)  # 전체 검색 결과를 목록으로 사용

    context = {
        'search_query_course_name': search_query_course_name,
        'search_query_instructor_name': search_query_instructor_name,
        'search_query_course_code': search_query_course_code,
        'search_results': search_results,
        'selected_summary': selected_summary,
        'selected_summary_id': selected_summary_id,  # 템플릿에서 현재 선택된 ID를 알 수 있도록 전달
    }
    return render(request, 'home/review_search_page.html', context) 