
from django.contrib import admin
from .models import (
    Department, Category, Semester, Student, Course,
    CourseSchedule,TimeTable, TimeTableDetail,
    Transcript, GraduationRequirement
)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('dept_id', 'dept_name')
    search_fields = ('dept_name',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'category_name', 'category_type', 'parent_category_id')
    search_fields = ('category_name', 'category_type')

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('semester_id', 'year', 'term', 'start_date', 'end_date',
                    'registration_start', 'registration_end')
    list_filter = ('year', 'term')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'student_name', 'dept_id', 'admission_year', 'email')
    list_filter = ('admission_year', 'dept_id')
    search_fields = ('student_name', 'email')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_id', 'course_code', 'section', 'dept_id',
                    'category_id', 'course_name', 'credit', 'instructor', 'course_type')
    search_fields = ('course_code', 'course_name', 'instructor')
    list_filter = ('course_type', 'year', 'dept_id', 'category_id')

@admin.register(CourseSchedule)
class CourseScheduleAdmin(admin.ModelAdmin):
    list_display = ('schedule_id', 'course_id', 'day', 'times', 'location')
    list_filter = ('day',)

@admin.register(TimeTable)
class TimeTableAdmin(admin.ModelAdmin):
    list_display = ('timetable_id', 'student_id', 'semester_id', 'title', 'created_at')
    list_filter = ('semester_id',)

@admin.register(TimeTableDetail)
class TimeTableDetailAdmin(admin.ModelAdmin):
    list_display = ('detail_id', 'timetable', 'course', 'schedule_info', 'user_note', 'custom_color')
    search_fields = ('schedule_info', 'user_note')

@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ('transcript_id', 'student_id_id', 'course_id_id', 'semester_id_id',
                    'grade', 'credit_taken', 'retake_available')
    list_filter = ('semester_id_id', 'grade', 'retake_available')

@admin.register(GraduationRequirement)
class GraduationRequirementAdmin(admin.ModelAdmin):
    list_display = ('requirement_id', 'dept_id_id', 'admission_year')
    list_filter = ('dept_id_id', 'admission_year')
    search_fields = ('dept_id__course__course_name',)
