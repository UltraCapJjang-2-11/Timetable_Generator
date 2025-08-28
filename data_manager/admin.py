from django.contrib import admin
from .models import *

@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ('university_id', 'university_name')
    search_fields = ('university_name',)

@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ('college_id', 'college_name', 'university')
    list_filter = ('university',)
    search_fields = ('college_name',)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('dept_id', 'dept_name', 'university', 'college')
    list_filter = ('university', 'college')
    search_fields = ('dept_name',)

@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    list_display = ('major_id', 'major_name', 'dept')
    list_filter = ('dept',)
    search_fields = ('major_name',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'category_name', 'category_level', 'version_year')
    list_filter = ('category_level', 'version_year')
    search_fields = ('category_name',)

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = (
        'semester_id', 'year', 'term', 'start_date', 'end_date',
        'course_registration_start', 'course_registration_end'
    )
    list_filter = ('year', 'term')
    search_fields = ('term',)

@admin.register(Courses)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        'course_id', 'course_code', 'section', 'course_name',
        'credits', 'target_year', 'grade_type', 'instructor_name'
    )
    list_filter = ('target_year', 'grade_type', 'semester')
    search_fields = ('course_code', 'course_name')

@admin.register(CourseSchedule)
class CourseScheduleAdmin(admin.ModelAdmin):
    list_display = ('schedule_id', 'course', 'day', 'times', 'location')
    list_filter = ('day',)
    search_fields = ('location',)

@admin.register(GraduationRequirement)
class GraduationRequirementAdmin(admin.ModelAdmin):
    list_display = ('requirement_id', 'dept', 'applicable_year', 'maximum_value', 'minimum_value')
    list_filter = ('dept', 'applicable_year')
    search_fields = ('description',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'college', 'department', 'minor', 'double_major', 'current_grade', 'completed_semesters')
    list_filter = ('college', 'department')
    search_fields = ('user__last_name',)

@admin.register(TimeTable)
class TimeTableAdmin(admin.ModelAdmin):
    list_display = ('timetable_id', 'user_profile', 'semester', 'title', 'created_at')
    list_filter = ('user_profile', 'semester')
    search_fields = ('title',)

@admin.register(TimeTableDetail)
class TimeTableDetailAdmin(admin.ModelAdmin):
    list_display = ('detail_id', 'timetable', 'course', 'schedule_info')
    list_filter = ('timetable', 'course')
    search_fields = ('schedule_info',)


@admin.register(GraduationRecord)
class GraduationRecordAdmin(admin.ModelAdmin):
    # 목록 페이지에 표시할 컬럼
    list_display = ('id', 'user_id','user_name','user_major','user_year','total_credits','major_credits',
                    'general_credits','free_credits','created_at',)
    # 필터 사이드바
    list_filter = ('user_major','user_year','created_at',)
    # 검색 박스 대상 필드
    search_fields = ('user_id','user_name',)

@admin.register(CourseSumm)
class CourseSummAdmin(admin.ModelAdmin):
    list_display = (
        'course',
        'group_activity',
    )
    list_select_related = ('course',)
    list_filter = ('group_activity',)
    search_fields = ('course__course_name', 'course__course_code')
    fieldsets = (
        (None, {
            'fields': ('course', 'course_summarization', 'group_activity')
        }),
    )

@admin.register(CourseReviewSummary)
class CourseReviewSummaryAdmin(admin.ModelAdmin):
    list_display = ('course_code', 'course_name', 'instructor_name', 'review_count', 'avg_rating', 'updated_at')
    search_fields = ('course_code', 'course_name', 'instructor_name')
    list_filter = ('instructor_name',)
    readonly_fields = ('updated_at',)

@admin.register(UserReview)
class UserReviewAdmin(admin.ModelAdmin):
    list_display = ('summary', 'rating', 'semester', 'created_at')
    search_fields = ('summary__course_code', 'summary__instructor_name', 'comment_text')
    list_filter = ('semester',)
    readonly_fields = ('created_at',)