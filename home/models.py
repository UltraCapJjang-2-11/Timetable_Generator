from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

# Student 모델을 위한 커스텀 User Manager
class StudentManager(BaseUserManager):
    def create_user(self, student_id, email, password=None, **extra_fields):
        """일반 사용자 생성"""
        if not student_id:
            raise ValueError("The Student ID must be set")
        if not email:
            raise ValueError("The Email must be set")

        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)

        user = self.model(student_id=student_id, email=email, **extra_fields)
        user.set_password(password)  # 비밀번호 암호화
        user.save(using=self._db)
        return user

    def create_superuser(self, student_id, email, password=None, **extra_fields):
        """슈퍼유저 생성"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(student_id, email, password, **extra_fields)

# 유저(Student)
class Student(AbstractUser):
    id = models.BigAutoField(primary_key=True)  # ✅ 기본 키 명시적으로 추가
    student_id = models.CharField(max_length=10, unique=True)  # 학번을 로그인 ID로 사용
    username = None  # 기본 username 제거
    email = models.EmailField(unique=True)  # 이메일 필수
    USERNAME_FIELD = 'student_id'  # 학번을 로그인 ID로 사용
    REQUIRED_FIELDS = ['email']  # 회원가입 시 이메일 필수

    # ✅ 학생 정보 추가
    department = models.CharField(max_length=50, blank=True, null=True)  # 학과
    year = models.IntegerField(blank=True, null=True)  # 학년
    current_total_credits = models.IntegerField(default=0)  # 현재 총 학점
    current_major_credits = models.IntegerField(default=0)  # 전공 학점
    current_elective_credits = models.IntegerField(default=0)  # 교양 학점

    objects = StudentManager()  # ✅ 커스텀 User Manager 적용

    def __str__(self):
        return f"{self.student_id} - {self.email} ({self.department}, {self.year}학년)"

# 교수 테이블
class Professor(models.Model):
    professor_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=50, blank=True, null=True)
    department = models.CharField(max_length=50)

    def __str__(self):
        return self.name

# 강의 테이블
class Course(models.Model):
    COURSE_TYPE_CHOICES = [
        ('전공', '전공'),
        ('교양', '교양'),
    ]

    REQUIREMENT_CHOICES = [
        ('필수', '필수'),
        ('선택', '선택'),
        ('없음', '없음'),
    ]

    course_id = models.AutoField(primary_key=True)
    course_code = models.CharField(max_length=20, unique=True)
    course_name = models.CharField(max_length=100)
    department = models.CharField(max_length=50)
    credits = models.IntegerField()
    course_type = models.CharField(max_length=10, choices=COURSE_TYPE_CHOICES)
    requirement = models.CharField(max_length=10, choices=REQUIREMENT_CHOICES, default='없음')
    semester = models.CharField(max_length=20)
    professor = models.ForeignKey(Professor, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.course_name} ({self.course_code})"

# 강의 시간 및 강의실 테이블
class ClassTime(models.Model):
    DAYS_CHOICES = [
        ('월', '월요일'),
        ('화', '화요일'),
        ('수', '수요일'),
        ('목', '목요일'),
        ('금', '금요일'),
        ('토', '토요일'),
        ('일', '일요일'),
    ]

    class_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    day = models.CharField(max_length=10, choices=DAYS_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.course.course_name} - {self.day} {self.start_time}~{self.end_time}"

# 목표 학점 테이블
class StudentGoal(models.Model):
    goal_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    semester = models.CharField(max_length=20)
    total_credits = models.IntegerField()
    major_credits = models.IntegerField()
    elective_credits = models.IntegerField()

    def __str__(self):
        return f"{self.student.name} - {self.semester} 목표 학점"