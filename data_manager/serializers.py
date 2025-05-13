from rest_framework import serializers
from data_manager.models import (
    Department, Category, Semester, Student, Courses,
    CourseSchedule, TimeTable, TimeTableDetail,
    Transcript, GraduationRequirement
)

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

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Courses
        fields = '__all__'

class CourseScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseSchedule
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

