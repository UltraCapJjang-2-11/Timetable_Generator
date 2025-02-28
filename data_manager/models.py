from django.db import models

############################################
# 3.1 DEPARTMENT
############################################
class Department(models.Model):
    dept_id = models.AutoField(primary_key=True)
    dept_name = models.CharField(max_length=255)

    class Meta:
        db_table = 'DEPARTMENT'
        managed = False

    def __str__(self):
        return f"[{self.dept_id}] {self.dept_name}"


############################################
# 3.2 CATEGORY
############################################
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    parent_category_id = models.ForeignKey(
        'self',
        models.SET_NULL,
        db_column='parent_category_id',
        null=True, blank=True
    )
    category_name = models.CharField(max_length=255)
    category_type = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'CATEGORY'
        managed = False

    def __str__(self):
        return self.category_name


############################################
# 3.3 SEMESTER
############################################
class Semester(models.Model):
    semester_id = models.AutoField(primary_key=True)
    year = models.IntegerField()
    term = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    registration_start = models.DateField()
    registration_end = models.DateField()

    class Meta:
        db_table = 'SEMESTER'
        managed = False

    def __str__(self):
        return f"{self.year} {self.term}"


############################################
# 3.4 STUDENT
############################################
class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    dept_id = models.ForeignKey(
        Department,
        models.CASCADE,
        db_column='dept_id'
    )
    admission_year = models.IntegerField()
    student_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)

    class Meta:
        db_table = 'STUDENT'
        managed = False

    def __str__(self):
        return f"{self.student_name} (ID: {self.student_id})"


############################################
# 3.5 COURSE (PK: course_id)
############################################
class Course(models.Model):
    course_id = models.AutoField(primary_key=True)
    course_code = models.CharField(max_length=20)
    section = models.CharField(max_length=5)
    dept_id = models.ForeignKey(
        Department,
        models.CASCADE,
        db_column='dept_id'
    )
    category_id = models.ForeignKey(
        Category,
        models.CASCADE,
        db_column='category_id'
    )
    year = models.CharField(max_length=20)
    course_type = models.CharField(max_length=50)  # 예: 전공필수, 전공선택, 교양, 교직, 일반선택 등
    course_name = models.CharField(max_length=255)
    credit = models.IntegerField()
    class_type = models.CharField(max_length=50)  # 강의구분 (예: 일반)
    grade_type = models.CharField(max_length=50)
    foreign_course = models.CharField(max_length=50, blank=True, null=True)
    instructor = models.CharField(max_length=255)
    lecture_hours = models.DecimalField(max_digits=4, decimal_places=1)
    lecture_units = models.DecimalField(max_digits=4, decimal_places=1)
    lab_hours = models.DecimalField(max_digits=4, decimal_places=1)
    lab_units = models.DecimalField(max_digits=4, decimal_places=1)
    semester_id = models.ForeignKey(
        Semester,
        models.CASCADE,
        db_column='semester_id',
        null=True  # 스키마 상 NOT NULL이 아니므로 null 허용
    )
    pre_enrollment_count = models.IntegerField(default=0)
    capacity = models.IntegerField(default=0)
    enrolled_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'COURSE'
        managed = False
        unique_together = (('course_code', 'section'),)

    def __str__(self):
        return f"[CID: {self.course_id}] {self.course_code}-{self.section} / {self.course_name}"


############################################
# 3.6 COURSE_SCHEDULE (schedule_id가 PK)
############################################
class CourseSchedule(models.Model):
    schedule_id = models.AutoField(primary_key=True)
    course_id = models.ForeignKey(
        Course,
        models.CASCADE,
        db_column='course_id'
    )
    day = models.CharField(max_length=10)
    times = models.CharField(max_length=50)
    location = models.CharField(max_length=255)

    class Meta:
        db_table = 'COURSE_SCHEDULE'
        managed = False

    def __str__(self):
        return f"[{self.schedule_id}] {self.course_id} / {self.day} [{self.location}]"


############################################
# 3.7 COURSE_OFFERING  (사용 안함)
############################################
# class CourseOffering(models.Model):
#     offering_id = models.AutoField(primary_key=True)
#     course_id = models.ForeignKey(
#         Course,
#         models.CASCADE,
#         db_column='course_id'
#     )
#     semester_id = models.ForeignKey(
#         Semester,
#         models.CASCADE,
#         db_column='semester_id'
#     )
#     pre_enrollment_count = models.IntegerField()
#     capacity = models.IntegerField()
#     enrolled_count = models.IntegerField()
#
#     class Meta:
#         db_table = 'COURSE_OFFERING'
#         managed = False
#
#     def __str__(self):
#         return f"Offering {self.offering_id} (Course: {self.course_id_id})"


############################################
# 3.8 TIME_TABLE
############################################
class TimeTable(models.Model):
    timetable_id = models.AutoField(primary_key=True)
    student_id = models.ForeignKey(
        Student,
        models.CASCADE,
        db_column='student_id'
    )
    semester_id = models.ForeignKey(
        Semester,
        models.CASCADE,
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
# 3.9 TIME_TABLE_DETAIL
############################################
class TimeTableDetail(models.Model):
    detail_id = models.AutoField(primary_key=True)
    timetable = models.ForeignKey(
        'TimeTable',
        models.CASCADE,
        db_column='timetable_id'
    )
    course = models.ForeignKey(
        'Course',
        models.CASCADE,
        db_column='course_id'
    )
    schedule_info = models.CharField(max_length=255)
    user_note = models.TextField(default='')
    custom_color = models.CharField(max_length=50, default='#FFFFFF')

    class Meta:
        db_table = 'TIME_TABLE_DETAIL'
        managed = False  # Django가 테이블 생성/수정하지 않도록 함
        unique_together = (('timetable', 'course'),)

    def __str__(self):
        return f"TTDetail {self.detail_id} - Table {self.timetable_id} / Course {self.course_id}"

############################################
# 3.10 TRANSCRIPT
############################################
class Transcript(models.Model):
    transcript_id = models.AutoField(primary_key=True)
    student_id = models.ForeignKey(
        Student,
        models.CASCADE,
        db_column='student_id'
    )
    course_id = models.ForeignKey(
        Course,
        models.CASCADE,
        db_column='course_id'
    )
    semester_id = models.ForeignKey(
        Semester,
        models.CASCADE,
        db_column='semester_id'
    )
    grade = models.CharField(max_length=2, default='NA')
    credit_taken = models.IntegerField(default=0)
    retake_available = models.BooleanField(default=True)

    class Meta:
        db_table = 'TRANSCRIPT'
        managed = False

    def __str__(self):
        return f"Transcript {self.transcript_id} - S{self.student_id_id}, C{self.course_id_id}"


############################################
# 3.11 GRADUATION_REQUIREMENT
############################################
class GraduationRequirement(models.Model):
    requirement_id = models.AutoField(primary_key=True)
    dept_id = models.ForeignKey(
        Department,
        models.CASCADE,
        db_column='dept_id'
    )
    admission_year = models.IntegerField()
    requirements_meta = models.TextField()

    class Meta:
        db_table = 'GRADUATION_REQUIREMENT'
        managed = False

    def __str__(self):
        return f"GradReq {self.requirement_id} / Dept {self.dept_id_id}"
