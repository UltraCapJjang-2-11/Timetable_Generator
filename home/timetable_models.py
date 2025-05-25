from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SavedTimetable(models.Model):
    """저장된 시간표 메인 테이블"""
    user_id = models.IntegerField()  # auth_user의 id 참조
    title = models.CharField(max_length=255)
    semester_year = models.IntegerField(default=2025)
    semester_term = models.CharField(max_length=10, default='1학기')
    total_credits = models.IntegerField(default=0)
    major_credits = models.IntegerField(default=0)
    elective_credits = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'saved_timetables'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} (사용자 ID: {self.user_id})"


class SavedTimetableCourse(models.Model):
    """저장된 시간표의 과목 정보"""
    timetable = models.ForeignKey(SavedTimetable, on_delete=models.CASCADE, related_name='courses')
    course_id = models.IntegerField(null=True, blank=True)  # courses 테이블의 course_id 참조
    course_name = models.CharField(max_length=255)
    course_code = models.CharField(max_length=50, blank=True)
    credits = models.IntegerField()
    category = models.CharField(max_length=100, blank=True)
    instructor = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    user_note = models.TextField(blank=True)
    custom_color = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'saved_timetable_courses'

    def __str__(self):
        return f"{self.course_name} ({self.timetable.title})"


class SavedTimetableSchedule(models.Model):
    """저장된 시간표의 스케줄 정보"""
    timetable_course = models.ForeignKey(SavedTimetableCourse, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=10)  # 월, 화, 수, 목, 금
    start_time = models.CharField(max_length=10)   # 09:00
    end_time = models.CharField(max_length=10)     # 12:00
    time_slots = models.CharField(max_length=50)   # "02,03,04"
    location = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'saved_timetable_schedules'

    def __str__(self):
        return f"{self.timetable_course.course_name} - {self.day_of_week} {self.start_time}-{self.end_time}" 