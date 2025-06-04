from data_manager.models import CourseReviewSummary, UserReview
from django.db.models import Q, F, Value, CharField 
from django.db.models.functions import Concat, Coalesce 


class ReviewService:
    """
    사용자 리뷰에 대한 서비스를 제공하는 클래스
    - 단일 조건 필터 메서드(강의명, 과목코드, 교수명)을 통해 리뷰를 검색
    - 종합적으로 필터링하여 결과를 반환하는 메서드 get_reviews 제공
    - summary_id 를 통해 User_reviews를 조회하는 메서드(get_reviews)
    """
    def get_all_review_summary(self):
        """
        기본적으로 전체 review_summary를 반환
        """
        return CourseReviewSummary.objects.all()

    def get_all_user_review(self):
        """
        기본적으로 전체 User Review 를 반환
        """
        return UserReview.objects.all()

    def filter_by_summary_id(self, queryset, summary_id):
        """
        course_name(강의이름)을 통해 course_review_summaries 테이블에서 리뷰 검색
        강의이름 중 일부가 포함된 결과 전부 가져온다.
        """
        if queryset is None:
            queryset = CourseReviewSummary.objects.all()
        if summary_id:
            queryset = queryset.filter(summary_id=summary_id)
        return queryset

    def filter_by_course_name(self, queryset, course_name):
        """
        course_name(강의이름)을 통해 course_review_summaries 테이블에서 리뷰 검색
        강의이름 중 일부가 포함된 결과 전부 가져온다.
        """
        if queryset is None:
            queryset = CourseReviewSummary.objects.all()
        if course_name:
            queryset = queryset.filter(course_name__icontains=course_name)
        return queryset

    def filter_by_course_code(self, queryset, course_code):
        """
        course_code(과목코드)을 통해 course_review_summaries 테이블에서 리뷰 검색
        정확하게 과목 코드와 같은 리뷰만 가져온다.
        """
        if queryset is None:
            queryset = CourseReviewSummary.objects.all()
        if course_code:
            queryset = queryset.filter(course_code=course_code)
        return queryset

    def filter_by_instructor_name(self, queryset, inst_name):
        """
        instructor_name(강사이름)을 통해 course_review_summaries 테이블에서 리뷰 검색
        강사이름 중 일부가 포함된 결과 전부 가져온다.
        """
        if queryset is None:
            queryset = CourseReviewSummary.objects.all()
        if inst_name:
            queryset = queryset.filter(instructor_name__icontains=inst_name)
        return queryset

    def get_reviews(
            self,
            summary_id=None,
            course_name=None,
            course_code=None,
            inst_name=None
    ):
        """
        여러 조건을 동시에 받아서 필터링 체이닝. course_review_summaries 테이블에서 리뷰 검색
        """
        queryset = CourseReviewSummary.objects.all()

        if summary_id:
            queryset = self.filter_by_summary_id(queryset, summary_id)

        if course_name:
            queryset = self.filter_by_course_name(queryset, course_name)

        if course_code:
            queryset = self.filter_by_course_code(queryset, course_code)

        if inst_name:
            queryset = self.filter_by_instructor_name(queryset, inst_name)

        return queryset

    def get_user_reviews(self, summary_id):
        """
        summary_id를 통해 해당하는 user_review 들을 조회하고, 
        각 리뷰에 대해 '년도 학기' 형태의 semester_str 필드를 추가합니다.
        """
        if not summary_id:
            return UserReview.objects.none()  # summary_id가 없으면 빈 쿼리셋 반환
        
        queryset = UserReview.objects.filter(summary__summary_id=summary_id)\
                                   .select_related('semester')\
                                   .annotate(
                                       semester_str=Coalesce(
                                           Concat(F('semester__year'), Value('년 '), F('semester__term'), output_field=CharField()),
                                           Value('학기 정보 없음', output_field=CharField())
                                       )
                                   )

        # CourseReviewSummary 모델의 summary_id (PK)를 통해 UserReview를 필터링합니다.
        # UserReview 모델에는 summary 라는 ForeignKey 필드가 CourseReviewSummary를 참조하고 있습니다.
        return queryset
