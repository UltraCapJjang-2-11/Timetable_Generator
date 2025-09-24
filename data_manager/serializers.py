from rest_framework import serializers
from data_manager.models import *

class CollegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Courses
        fields = '__all__'

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class SemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Semester
        fields = '__all__'

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'

class CourseScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseSchedule
        fields = ['day', 'times', 'location']


class CourseSerializer(serializers.ModelSerializer):
    """
    강의 정보를 직렬화하면서, category와 semester 정보를
    ID가 아닌 이름과 포맷된 문자열로 보여줍니다.
    """
    # 1. 기존 category, semester 필드를 대체할 새로운 필드 정의
    category_name = serializers.SerializerMethodField()
    semester = serializers.SerializerMethodField()
    dept_name = serializers.SerializerMethodField()
    # CourseSchedule 정보(schedules)를 함께 보여주기 위해 추가
    schedules = CourseScheduleSerializer(many=True, read_only=True, source='courseschedule_set')

    class Meta:
        model = Courses
        fields = [
            'course_id',
            'schedules',
            'course_name',
            'course_code',
            'section',
            'credits',
            'target_year',
            'foreign_course',
            'instructor_name',
            'capacity',
            'dept_name',
            'category_name',
            'semester',
        ]

    def get_dept_name(self, obj):
        return obj.dept.dept_name if obj.dept else None

    # SerializerMethodField의 값을 어떻게 만들지 정의하는 메소드
    def get_category_name(self, obj):
        """
        Courses 객체(obj)의 category(ForeignKey)를 통해
        Category 모델의 category_name을 가져옵니다.
        교양 과목의 경우 상위 분류로 통일합니다.
        """
        # obj.category가 None일 경우를 대비하여 안전하게 처리
        if not obj.category:
            return None

        category = obj.category

        # 카테고리 레벨이 2이고, 부모의 부모가 "교양"인 경우
        if (category.category_level == 2 and
                category.parent_category and
                category.parent_category.parent_category and
                category.parent_category.parent_category.category_name == "교양"):
            # 부모 카테고리(level 1)의 이름을 반환
            return category.parent_category.category_name

        # 그 외의 경우는 원래 카테고리 이름 반환
        return category.category_name

    def get_semester(self, obj):
        """
        Courses 객체(obj)의 semester(ForeignKey)를 통해
        Semester 모델의 year와 term을 조합하여 문자열을 만듭니다.
        """
        # obj.semester가 None일 경우를 대비하여 안전하게 처리
        if obj.semester:
            return f"{obj.semester.year} {obj.semester.term}"
        return None

class TimeTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeTable
        fields = '__all__'

class TimeTableDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeTableDetail
        fields = '__all__'

class TranscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transcript
        fields = '__all__'

class GraduationRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = GraduationRequirement
        fields = '__all__'

class CourseSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseSumm
        fields = '__all__'

class CourseReviewSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseReviewSummary
        fields = ['summary_id', 'course_code', 'course_name', 'instructor_name', 'review_count', 'avg_rating', 'dist_json', 'updated_at', 'review_sum']

class UserReviewSerializer(serializers.ModelSerializer):
    summary_details = CourseReviewSummarySerializer(source='summary', read_only=True)
    semester_str = serializers.CharField(read_only=True) # annotate된 필드이므로 read_only

    class Meta:
        model = UserReview
        fields = ['user_review_id', 'summary', 'summary_details', 'rating', 'comment_text', 'semester', 'semester_str', 'is_anonymous']
