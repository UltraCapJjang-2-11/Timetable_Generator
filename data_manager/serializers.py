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

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'

class CourseScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseSchedule
        fields = ['day', 'times', 'location']

class CourseSerializer(serializers.ModelSerializer):
    schedules = CourseScheduleSerializer(
        source='courseschedule_set',  # 역참조 이름
        many=True,
        read_only=True
    )

    class Meta:
        model = Courses
        fields = '__all__'

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
        fields = ['user_review_id', 'summary', 'summary_details', 'student_id', 'rating', 'comment_text', 'semester_str', 'created_at', 'categories'] # semester_str, created_at, categories 추가
