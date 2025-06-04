# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    parent_category = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    category_name = models.CharField(max_length=255)
    category_level = models.IntegerField()
    version_year = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'category'


class Colleges(models.Model):
    college_id = models.AutoField(primary_key=True)
    university = models.ForeignKey('Universities', models.DO_NOTHING)
    college_name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'colleges'


class Course(models.Model):
    course_id = models.AutoField(primary_key=True)
    course_code = models.CharField(max_length=20)
    section = models.CharField(max_length=5)
    dept = models.ForeignKey('Department', models.DO_NOTHING)
    category = models.ForeignKey(Category, models.DO_NOTHING)
    year = models.CharField(max_length=20)
    course_type = models.CharField(max_length=50)
    course_name = models.CharField(max_length=255)
    credit = models.IntegerField()
    class_type = models.CharField(max_length=50)
    grade_type = models.CharField(max_length=50)
    foreign_course = models.CharField(max_length=50, blank=True, null=True)
    instructor = models.CharField(max_length=255)
    lecture_hours = models.DecimalField(max_digits=4, decimal_places=1)
    lecture_units = models.DecimalField(max_digits=4, decimal_places=1)
    lab_hours = models.DecimalField(max_digits=4, decimal_places=1)
    lab_units = models.DecimalField(max_digits=4, decimal_places=1)
    semester = models.ForeignKey('Semester', models.DO_NOTHING, blank=True, null=True)
    pre_enrollment_count = models.IntegerField()
    capacity = models.IntegerField()
    enrolled_count = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'course'


class CourseSchedule(models.Model):
    schedule_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, models.DO_NOTHING)
    day = models.CharField(max_length=10)
    times = models.CharField(max_length=50)
    location = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'course_schedule'


class CourseSchedules(models.Model):
    schedule_id = models.AutoField(primary_key=True)
    course = models.ForeignKey('Courses', models.DO_NOTHING)
    day = models.CharField(max_length=10)
    times = models.CharField(max_length=50)
    location = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'course_schedules'


class Courses(models.Model):
    course_id = models.AutoField(primary_key=True)
    dept = models.ForeignKey('Departments', models.DO_NOTHING, blank=True, null=True)
    major = models.ForeignKey('Major', models.DO_NOTHING, blank=True, null=True)
    category = models.ForeignKey(Category, models.DO_NOTHING, blank=True, null=True)
    semester = models.ForeignKey('Semester', models.DO_NOTHING)
    course_name = models.CharField(max_length=255)
    course_code = models.CharField(max_length=50)
    section = models.CharField(max_length=10)
    credits = models.IntegerField()
    target_year = models.CharField(max_length=10)
    grade_type = models.CharField(max_length=50)
    foreign_course = models.CharField(max_length=50, blank=True, null=True)
    instructor_name = models.CharField(max_length=512, blank=True, null=True)
    lecture_hours = models.DecimalField(max_digits=4, decimal_places=1)
    lecture_times = models.DecimalField(max_digits=4, decimal_places=1)
    lab_hours = models.DecimalField(max_digits=4, decimal_places=1)
    lab_times = models.DecimalField(max_digits=4, decimal_places=1)
    pre_enrollment_count = models.IntegerField(blank=True, null=True)
    capacity = models.IntegerField(blank=True, null=True)
    enrolled_count = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'courses'


class Department(models.Model):
    dept_id = models.AutoField(primary_key=True)
    dept_name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'department'


class Departments(models.Model):
    dept_id = models.AutoField(primary_key=True)
    university = models.ForeignKey('Universities', models.DO_NOTHING)
    college = models.ForeignKey(Colleges, models.DO_NOTHING, blank=True, null=True)
    dept_name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'departments'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class GraduationRecord(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_id = models.IntegerField()
    total_credits = models.IntegerField()
    major_credits = models.IntegerField()
    general_credits = models.IntegerField()
    free_credits = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    missing_major_subjects = models.TextField(blank=True, null=True)
    user_student_id = models.CharField(max_length=50, blank=True, null=True)
    user_name = models.CharField(max_length=255, blank=True, null=True)
    user_major = models.CharField(max_length=255, blank=True, null=True)
    user_year = models.CharField(max_length=10, blank=True, null=True)
    total_requirement = models.IntegerField(blank=True, null=True)
    major_requirement = models.TextField(blank=True, null=True)
    general_requirement = models.TextField(blank=True, null=True)
    free_requirement = models.IntegerField(blank=True, null=True)
    missing_general_sub = models.TextField(blank=True, null=True)
    detailed_credits = models.TextField(blank=True, null=True)
    completed_courses = models.TextField(blank=True, null=True)
    major_required_credits = models.IntegerField(blank=True, null=True)
    major_elective_credits = models.IntegerField(blank=True, null=True)
    major_required_requirement = models.IntegerField(blank=True, null=True)
    major_elective_requirement = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'graduation_record'


class GraduationRequirement(models.Model):
    requirement_id = models.AutoField(primary_key=True)
    dept = models.ForeignKey(Department, models.DO_NOTHING)
    admission_year = models.IntegerField()
    requirements_meta = models.TextField()

    class Meta:
        managed = False
        db_table = 'graduation_requirement'


class Graduationrequirements(models.Model):
    requirement_id = models.AutoField(primary_key=True)
    dept = models.ForeignKey(Departments, models.DO_NOTHING)
    category = models.ForeignKey(Category, models.DO_NOTHING, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    maximum_value = models.IntegerField(blank=True, null=True)
    minimum_value = models.IntegerField(blank=True, null=True)
    applicable_year = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'graduationrequirements'


class Major(models.Model):
    major_id = models.AutoField(primary_key=True)
    dept = models.ForeignKey(Departments, models.DO_NOTHING)
    major_name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'major'


class Semester(models.Model):
    semester_id = models.AutoField(primary_key=True)
    year = models.IntegerField()
    term = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    course_registration_start = models.DateField()
    course_registration_end = models.DateField()

    class Meta:
        managed = False
        db_table = 'semester'


class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    dept = models.ForeignKey(Department, models.DO_NOTHING)
    admission_year = models.IntegerField()
    student_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'student'


class Students(models.Model):
    student_id = models.AutoField(primary_key=True)
    auth_user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    dept = models.ForeignKey(Departments, models.DO_NOTHING)
    admission_year = models.IntegerField()
    completed_semester = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'students'


class TimeTable(models.Model):
    timetable_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Students, models.DO_NOTHING)
    semester = models.ForeignKey(Semester, models.DO_NOTHING)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'time_table'


class TimeTableDetail(models.Model):
    detail_id = models.AutoField(primary_key=True)
    timetable = models.ForeignKey(TimeTable, models.DO_NOTHING)
    course = models.ForeignKey(Courses, models.DO_NOTHING)
    schedule_info = models.CharField(max_length=255)
    user_note = models.TextField(blank=True, null=True)
    custom_color = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'time_table_detail'
        unique_together = (('timetable', 'course'),)


class Transcript(models.Model):
    transcript_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Students, models.DO_NOTHING)
    course = models.ForeignKey(Courses, models.DO_NOTHING)
    semester = models.ForeignKey(Semester, models.DO_NOTHING)
    grade = models.CharField(max_length=2, blank=True, null=True)
    retake_available = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'transcript'


class Universities(models.Model):
    university_id = models.AutoField(primary_key=True)
    university_name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'universities'
