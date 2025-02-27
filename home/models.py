from django.db import models


# ✅ 학과 (Department)
class Department(models.Model):
    dept_id = models.AutoField(primary_key=True)
    dept_name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'department'

    def __str__(self):
        return self.dept_name


# ✅ 카테고리 (Category)
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    parent_category = models.ForeignKey(
        'self', models.DO_NOTHING, blank=True, null=True
    )
    category_name = models.CharField(max_length=255)
    category_type = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'category'

    def __str__(self):
        return self.category_name


# ✅ 강의 (Course)
class Course(models.Model):
    course_code = models.CharField(max_length=20, primary_key=True)  # ✅ 명확한 Primary Key 설정
    section = models.CharField(max_length=5)  # ✅ ForeignKey 대신 일반 필드 사용
    dept = models.ForeignKey(Department, models.DO_NOTHING)
    category = models.ForeignKey(Category, models.DO_NOTHING)
    year = models.CharField(max_length=20)
    course_type = models.CharField(max_length=50)
    course_name = models.CharField(max_length=255)
    credit = models.IntegerField()
    instructor = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'course'
        constraints = [
            models.UniqueConstraint(fields=['course_code', 'section'], name='unique_course_section')
        ]  # ✅ 복합 키 유지

    def __str__(self):
        return f"{self.course_name} ({self.course_code}-{self.section})"


# ✅ 강의 개설 정보 (CourseOffering)
class CourseOffering(models.Model):
    offering_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, models.DO_NOTHING, db_column='course_code')  # ✅ Course 참조
    section = models.CharField(max_length=5)  # ✅ ForeignKey 대신 일반 필드 사용
    semester = models.ForeignKey('Semester', models.DO_NOTHING)
    pre_enrollment_count = models.IntegerField()
    capacity = models.IntegerField()
    enrolled_count = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'course_offering'
        constraints = [
            models.UniqueConstraint(fields=['course', 'section'], name='unique_course_offering')
        ]


# ✅ 강의 스케줄 (CourseSchedule)
class CourseSchedule(models.Model):
    course = models.ForeignKey(Course, models.DO_NOTHING, db_column='course_code')  # ✅ Course 참조
    section = models.CharField(max_length=5)  # ✅ ForeignKey 대신 일반 필드 사용
    day = models.CharField(max_length=10)
    times = models.CharField(max_length=50)
    location = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'course_schedule'
        constraints = [
            models.UniqueConstraint(fields=['course', 'section', 'day', 'location'], name='unique_course_schedule')
        ]


# ✅ 학기 (Semester)
class Semester(models.Model):
    semester_id = models.AutoField(primary_key=True)
    year = models.IntegerField()
    term = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        managed = False
        db_table = 'semester'

    def __str__(self):
        return f"{self.year} - {self.term}"


# ✅ 학생 (Student)
class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    dept = models.ForeignKey(Department, models.DO_NOTHING)
    admission_year = models.IntegerField()
    student_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'student'

    def __str__(self):
        return self.student_name


# ✅ 시간표 (TimeTable)
class TimeTable(models.Model):
    timetable_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, models.DO_NOTHING)
    semester = models.ForeignKey(Semester, models.DO_NOTHING)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'time_table'


# ✅ 시간표 상세 정보 (TimeTableDetail)
class TimeTableDetail(models.Model):
    timetable = models.ForeignKey(TimeTable, models.DO_NOTHING)
    course = models.ForeignKey(Course, models.DO_NOTHING, db_column='course_code')  # ✅ Course 참조
    section = models.CharField(max_length=5)  # ✅ ForeignKey 대신 일반 필드 사용
    schedule_info = models.CharField(max_length=255)
    user_note = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'time_table_detail'
        constraints = [
            models.UniqueConstraint(fields=['timetable', 'course', 'section'], name='unique_timetable_detail')
        ]


# ✅ 성적 (Transcript)
class Transcript(models.Model):
    transcript_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, models.DO_NOTHING)
    course = models.ForeignKey(Course, models.DO_NOTHING, db_column='course_code')  # ✅ Course 참조
    section = models.CharField(max_length=5)  # ✅ ForeignKey 대신 일반 필드 사용
    semester = models.ForeignKey(Semester, models.DO_NOTHING)
    grade = models.CharField(max_length=2)
    credit_taken = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'transcript'
        constraints = [
            models.UniqueConstraint(fields=['student', 'course', 'section'], name='unique_transcript_course_section')
        ]
