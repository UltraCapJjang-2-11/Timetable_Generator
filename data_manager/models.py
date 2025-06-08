from django.db import models

############################################
# 1. University (Universities 테이블)
############################################
class University(models.Model):
    university_id = models.AutoField(primary_key=True)
    university_name = models.CharField(max_length=255)

    class Meta:
        db_table = 'Universities'
        managed = False

    def __str__(self):
        return self.university_name


############################################
# 2. College (Colleges 테이블)
############################################
class College(models.Model):
    college_id = models.AutoField(primary_key=True)
    university = models.ForeignKey(
        University,
        on_delete=models.CASCADE,
        db_column='university_id'
    )
    college_name = models.CharField(max_length=255)

    class Meta:
        db_table = 'Colleges'
        managed = False

    def __str__(self):
        return self.college_name


############################################
# 3. Department (Departments 테이블)
############################################
class Department(models.Model):
    dept_id = models.AutoField(primary_key=True)
    university = models.ForeignKey(
        University,
        on_delete=models.CASCADE,
        db_column='university_id'
    )
    college = models.ForeignKey(
        College,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='college_id'
    )
    dept_name = models.CharField(max_length=255)

    class Meta:
        db_table = 'Departments'
        managed = False

    def __str__(self):
        return f"[{self.dept_id}] {self.dept_name}"


############################################
# 4. Major (Major 테이블)
############################################
class Major(models.Model):
    major_id = models.AutoField(primary_key=True)
    dept = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        db_column='dept_id'
    )
    major_name = models.CharField(max_length=255)

    class Meta:
        db_table = 'Major'
        managed = False

    def __str__(self):
        return self.major_name


############################################
# 5. Category (Category 테이블)
############################################
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='parent_category_id'
    )
    category_name = models.CharField(max_length=255)
    category_level = models.IntegerField(default=0)
    version_year = models.IntegerField()

    class Meta:
        db_table = 'Category'
        managed = False

    def __str__(self):
        return self.category_name


############################################
# 6. Semester (SEMESTER 테이블)
############################################
class Semester(models.Model):
    semester_id = models.AutoField(primary_key=True)
    year = models.IntegerField()
    term = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    course_registration_start = models.DateField()
    course_registration_end = models.DateField()

    class Meta:
        db_table = 'SEMESTER'
        managed = False

    def __str__(self):
        return f"{self.year} {self.term}"


############################################
# 7. Course (Courses 테이블)
############################################
class Courses(models.Model):
    course_id = models.AutoField(primary_key=True)
    dept = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='dept_id'
    )
    major = models.ForeignKey(
        Major,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='major_id'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        db_column='category_id'
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        db_column='semester_id'
    )
    course_name = models.CharField(max_length=255)
    course_code = models.CharField(max_length=50)
    section = models.CharField(max_length=10)
    credits = models.IntegerField()
    target_year = models.CharField(max_length=10)
    grade_type = models.CharField(max_length=50)
    foreign_course = models.CharField(max_length=50, null=True, blank=True)
    instructor_name = models.CharField(max_length=255)
    lecture_hours = models.DecimalField(max_digits=4, decimal_places=1)
    lecture_times = models.DecimalField(max_digits=4, decimal_places=1)
    lab_hours = models.DecimalField(max_digits=4, decimal_places=1)
    lab_times = models.DecimalField(max_digits=4, decimal_places=1)
    pre_enrollment_count = models.IntegerField(default=0)
    capacity = models.IntegerField(default=0)
    enrolled_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'Courses'
        managed = False

    def __str__(self):
        return f"[{self.course_id}] {self.course_code}-{self.section} / {self.course_name}"


############################################
# 8. CourseSchedule (COURSE_SCHEDULES 테이블)
############################################
class CourseSchedule(models.Model):
    schedule_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(
        Courses,
        on_delete=models.CASCADE,
        db_column='course_id'
    )
    day = models.CharField(max_length=10)
    times = models.CharField(max_length=50)
    location = models.CharField(max_length=255)

    class Meta:
        db_table = 'course_schedules'
        managed = False

    def __str__(self):
        return f"[{self.schedule_id}] {self.course} - {self.day} at {self.location}"


############################################
# 9. GraduationRequirement (GraduationRequirements 테이블)
############################################
class GraduationRequirement(models.Model):
    requirement_id = models.AutoField(primary_key=True)
    dept = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        db_column='dept_id'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='category_id'
    )
    description = models.TextField(null=True, blank=True)
    maximum_value = models.IntegerField(default=0)
    minimum_value = models.IntegerField(default=0)
    applicable_year = models.IntegerField()

    class Meta:
        db_table = 'GraduationRequirements'
        managed = False

    def __str__(self):
        return f"GradReq {self.requirement_id} for Dept {self.dept.dept_id}"


############################################
# 10. Student (Students 테이블)
############################################
class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    auth_user_id = models.IntegerField()  # 필요시 auth.User와 연동 가능
    dept = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        db_column='dept_id'
    )
    admission_year = models.IntegerField()
    completed_semester = models.IntegerField(default=0)

    class Meta:
        db_table = 'Students'
        managed = False

    def __str__(self):
        return f"Student {self.student_id}"


############################################
# 11. TimeTable (TIME_TABLE 테이블)
############################################
class TimeTable(models.Model):
    timetable_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        db_column='student_id'
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        db_column='semester_id'
    )
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'TIME_TABLE'
        managed = False

    def __str__(self):
        return f"TimeTable {self.timetable_id} - {self.title}"


############################################
# 12. TimeTableDetail (TIME_TABLE_DETAIL 테이블)
############################################
class TimeTableDetail(models.Model):
    detail_id = models.AutoField(primary_key=True)
    timetable = models.ForeignKey(
        TimeTable,
        on_delete=models.CASCADE,
        db_column='timetable_id'
    )
    course = models.ForeignKey(
        Courses,
        on_delete=models.CASCADE,
        db_column='course_id'
    )
    schedule_info = models.CharField(max_length=255)
    user_note = models.TextField(null=True, blank=True)
    custom_color = models.CharField(max_length=50, default='#FFFFFF')

    class Meta:
        db_table = 'TIME_TABLE_DETAIL'
        managed = False
        unique_together = (('timetable', 'course'),)

    def __str__(self):
        return f"TimeTableDetail {self.detail_id} - TimeTable {self.timetable.timetable_id} / Course {self.course.course_id}"


############################################
# 13. Transcript (Transcript 테이블)
############################################
class Transcript(models.Model):
    transcript_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        db_column='student_id'
    )
    course = models.ForeignKey(
        Courses,
        on_delete=models.CASCADE,
        db_column='course_id'
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        db_column='semester_id'
    )
    grade = models.CharField(max_length=2, default='NA')
    retake_available = models.BooleanField(default=True)

    class Meta:
        db_table = 'Transcript'
        managed = False

    def __str__(self):
        return f"Transcript {self.transcript_id} - Student {self.student.student_id}, Course {self.course.course_id}"


class CourseSumm(models.Model):
    """
    Courses 테이블의 course_id를 PK 및 FK로 참조하는
    약한 엔티티(OneToOne) 모델입니다.
    """
    course = models.OneToOneField(
        Courses,
        on_delete=models.CASCADE,
        primary_key=True,
        verbose_name="강의"
    )
    course_summarization = models.TextField(
        verbose_name="강의 요약",
        help_text="강의에 대한 간략한 설명을 입력하세요."
    )
    group_activity = models.CharField(
        max_length=1,
        choices=[
            ('Y', '있음'),
            ('N', '없음'),
        ],
        default='N',
        verbose_name="조별 과제 여부",
        help_text="조별 과제가 있는 경우 'Y', 없는 경우 'N'을 선택하세요."
    )

    class Meta:
        db_table = 'course_summ'
        verbose_name = '강의 요약 정보'
        verbose_name_plural = '강의 요약 정보'
        managed = False

    def __str__(self):
        return f"{self.course.course_name} 요약"


## 14. Graduation_record 테이블 (임시)
class GraduationRecord(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_id = models.IntegerField()

    total_credits = models.IntegerField()
    major_credits = models.IntegerField()
    general_credits = models.IntegerField()
    free_credits = models.IntegerField()

    total_requirement = models.IntegerField(null=True, blank=True)
    free_requirement = models.IntegerField(null=True, blank=True)

    major_required_credits = models.IntegerField(default=0)
    major_elective_credits = models.IntegerField(default=0)

    major_required_requirement = models.IntegerField(null=True, blank=True)
    major_elective_requirement = models.IntegerField(null=True, blank=True)

    missing_major_subjects = models.TextField(blank=True)
    missing_general_sub = models.TextField(blank=True)

    major_requirement = models.TextField(blank=True)
    general_requirement = models.TextField(blank=True)

    detailed_credits = models.TextField(blank=True)
    completed_courses = models.TextField(blank=True)

    user_student_id = models.CharField(max_length=50, null=True, blank=True)
    user_name = models.CharField(max_length=255, null=True, blank=True)
    user_major = models.CharField(max_length=255, null=True, blank=True)
    user_year = models.CharField(max_length=10, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'graduation_record'
        managed = False

    def __str__(self):
        return f"{self.user_name or self.user_id} ({self.user_student_id})"


class CourseReviewSummary(models.Model):
    summary_id = models.AutoField(primary_key=True)
    course_code = models.CharField("강의코드", max_length=20)
    course_name = models.CharField("강의명", max_length=200)
    instructor_name = models.CharField("교수명", max_length=100)

    review_count = models.IntegerField("리뷰 개수")
    avg_rating = models.DecimalField("평균 평점", max_digits=3, decimal_places=2)
    dist_json = models.JSONField("분포 JSON")  # 전체 통계 분포 저장
    updated_at = models.DateTimeField("최종 갱신일", auto_now=True)

    review_sum = models.TextField("리뷰 요약", null=True, blank=True)

    class Meta:
        db_table = 'course_review_summaries'
        verbose_name = "강의별 요약 통계"
        verbose_name_plural = "강의별 요약 통계"
        managed = False

    def __str__(self):
        return f"{self.course_code} - {self.instructor_name}"

    def get_formatted_distribution(self):
        if not self.dist_json or not isinstance(self.dist_json, dict):
            return []

        # 카테고리 및 항목에 대한 한글 레이블 정의
        category_labels = {
            "grade": "학점 만족도",
            "assign": "과제량",
            "group_activity": "팀플 유무/빈도"
        }

        item_labels = {
            "grade": {
                "many": "너그러움",  # 사용자의 설명: many(너그러움)
                "normal": "보통",    # 사용자의 설명: normal(보통)
                "none": "깐깐함"     # 사용자의 설명: none(깐깐함)
            },
            "assign": {
                "many": "많음",
                "normal": "보통",
                "none": "없음"
            },
            "group_activity": {
                "many": "많음/자주 있음",
                "normal": "보통/가끔 있음",
                "none": "없음"
            }
        }
        
        # 항목 표시 순서 정의 (예: 긍정적 -> 중립 -> 부정적 순서로)
        item_order = ['many', 'normal', 'none']

        formatted_data = []

        for category_key, items_data in self.dist_json.items():
            if not isinstance(items_data, dict):
                continue # items_data가 dict가 아니면 건너뛰기

            category_display_label = category_labels.get(category_key, category_key.replace("_", " ").title())
            
            # 해당 카테고리의 전체 응답 수 계산
            total_count_for_category = sum(items_data.values())
            
            processed_items = []
            if total_count_for_category > 0:
                for item_key in item_order: # 정의된 순서대로 처리
                    if item_key in items_data:
                        count = items_data[item_key]
                        item_display_label = item_labels.get(category_key, {}).get(item_key, item_key.title())
                        percentage = (count / total_count_for_category) * 100
                        processed_items.append({
                            'label': item_display_label,
                            'key': item_key,
                            'count': count,
                            'percentage': round(percentage, 1) # 소수점 첫째 자리까지
                        })
            
            if processed_items: # 처리된 항목이 있을 경우에만 추가
                formatted_data.append({
                    'category_label': category_display_label,
                    'items': processed_items,
                    'total_responses': total_count_for_category
                })
                
        return formatted_data


class UserReview(models.Model):
    user_review_id = models.AutoField(primary_key=True)
    summary = models.ForeignKey(
        CourseReviewSummary,
        verbose_name="요약 통계",
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    # student 모델을 사용 중이라면 아래 라인을 활성화하고 import 도 맞춰주세요.
    # student = models.ForeignKey(Student, verbose_name="학생", null=True, blank=True, on_delete=models.SET_NULL)
    student_id = models.IntegerField("학생 ID", null=True, blank=True)

    rating = models.DecimalField("별점", max_digits=2, decimal_places=1)
    comment_text = models.TextField("리뷰 본문", null=True, blank=True)
    categories = models.JSONField("카테고리 선택", default=dict)  # {"assign":"none", ...}
    semester = models.ForeignKey(
        Semester,
        verbose_name="학기",
        null=True, blank=True,
        on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField("작성일", auto_now_add=True)

    class Meta:
        db_table = 'user_review'
        verbose_name = "개별 강의평"
        verbose_name_plural = "개별 강의평"
        managed = False

    def __str__(self):
        return f"{self.summary} / {self.rating}점"

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
        managed = False

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
        managed = False

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
        managed = False

    def __str__(self):
        return f"{self.timetable_course.course_name} - {self.day_of_week} {self.start_time}-{self.end_time}"