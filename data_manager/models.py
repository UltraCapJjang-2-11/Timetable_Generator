from django.db import models
from django.contrib.auth.models import User


# University (ex. 충북대학교)
class University(models.Model):
    university_id = models.AutoField(primary_key=True)
    university_name = models.CharField(max_length=255)

    class Meta:
        db_table = 'Universities'

    def __str__(self):
        return self.university_name


# College (ex. 전자정보대학)
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

    def __str__(self):
        return self.college_name


# Department (ex. 소프트웨어학부)
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

    def __str__(self):
        return f"[{self.dept_id}] {self.dept_name}"


# Major (ex. 인공지능전공)
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

    def __str__(self):
        return self.major_name


# Category (ex. 전공)
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

    def __str__(self):
        return self.category_name


# Semester
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

    def __str__(self):
        return f"{self.year} {self.term}"


# Course
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
    target_year = models.CharField(max_length=50)
    grade_type = models.CharField(max_length=20, null=True, blank=True)
    foreign_course = models.CharField(max_length=20, null=True, blank=True)
    instructor_name = models.CharField(max_length=255, null=True, blank=True)
    lecture_hours = models.DecimalField(max_digits=4, decimal_places=1)
    lecture_times = models.DecimalField(max_digits=4, decimal_places=1)
    lab_hours = models.DecimalField(max_digits=4, decimal_places=1)
    lab_times = models.DecimalField(max_digits=4, decimal_places=1)
    pre_enrollment_count = models.IntegerField(default=0)
    capacity = models.IntegerField(default=0)
    enrolled_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'Courses'
        unique_together = (('course_code', 'semester_id', 'section'),)

    def __str__(self):
        return f"[{self.course_id}] {self.course_code}-{self.section} / {self.course_name}"


# CourseSchedule
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

    def __str__(self):
        return f"[{self.schedule_id}] {self.course} - {self.day} at {self.location}"


# GraduationRequirement
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

    def __str__(self):
        return f"GradReq {self.requirement_id} for Dept {self.dept.dept_id}"


# UserProfile
class UserProfile(models.Model):
    """
    Django의 기본 User 모델을 확장하여 학사 정보를 저장
    """
    # Django의 기본 User 모델과 1:1로 연결합니다.
    # User가 삭제되면 UserProfile도 함께 삭제됩니다.
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)

    # 사용자가 온보딩 중 어디까지 진행했는지를 나타내는 상태 플레그
    ONBOARDING_STATUS_CHOICES = [
        ('ACCOUNT_CREATED', '계정 생성 완료'),
        ('PDF_UPLOADED', 'PDF 업로드 완료'),
        ('INFO_CONFIRMED', '학사 정보 확인 완료'),
        ('COMPLETED', '온보딩 최종 완료'),
    ]

    # 대학
    college = models.ForeignKey(
        'College',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="단과대학"
    )

    # 학과(전공)
    department = models.ForeignKey(
        'Department',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="학과(전공)"
    )
    # 부전공
    minor = models.ForeignKey(
        'Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='minor_profiles',
        verbose_name="부전공"
    )
    # 다전공
    double_major = models.ForeignKey(
        'Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='double_major_profiles',
        verbose_name="다전공"
    )

    # # 5. 과정 (e.g., 학부, 대학원)
    # ACADEMIC_LEVEL_CHOICES = [
    #     ('UG', '학부'),
    #     ('GR', '대학원'),
    # ]
    # academic_level = models.CharField(
    #     max_length=2,
    #     choices=ACADEMIC_LEVEL_CHOICES,
    #     default='UG',
    #     verbose_name="과정"
    # )

    # 적용 졸업 요건
    rule_set = models.ForeignKey(
        'RuleSet',
        on_delete=models.SET_NULL,  # RuleSet이 삭제되더라도 UserProfile은 유지
        null=True,  # 아직 할당되지 않은 사용자가 있을 수 있음
        blank=True,  # 관리자 페이지 등에서 비워둘 수 있도록 허용
        verbose_name="적용 규칙 묶음"
    )

    admission_year = models.PositiveSmallIntegerField(
        verbose_name="입학년도",
        help_text="교과 적용 연도로 사용됩니다.",
        null=True, blank=True
    )
    current_grade = models.PositiveSmallIntegerField(
        verbose_name="학년",
        null=True, blank=True
    )
    completed_semesters = models.PositiveSmallIntegerField(
        verbose_name="이수 학기",
        null=True, blank=True
    )

    user_name = models.CharField(
        max_length=255,
        null=True, blank=True,
        verbose_name="사용자 이름"
    )

    user_student_id = models.CharField(
        max_length=255,
        null=True, blank=True,
        verbose_name="사용자 학번"
    )

    # 온보딩 상태 추적
    onboarding_status = models.CharField(
        max_length=20,
        choices=ONBOARDING_STATUS_CHOICES,
        default='ACCOUNT_CREATED'
    )

    class Meta:
        db_table = 'UserProfile'
        verbose_name = '사용자 프로필'
        verbose_name_plural = '사용자 프로필'

    def __str__(self):
        return self.user.username


# TimeTable
class TimeTable(models.Model):
    timetable_id = models.AutoField(primary_key=True)
    # 필드명을 user_profile로 명확히 하고, db_column 제거
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'time_table'

    def __str__(self):
        return f"TimeTable {self.timetable_id} - {self.title}"


# TimeTableDetail
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

        unique_together = (('timetable', 'course'),)

    def __str__(self):
        return f"TimeTableDetail {self.detail_id} - TimeTable {self.timetable.timetable_id} / Course {self.course.course_id}"


# Transcript
class Transcript(models.Model):
    """
    사용자(UserProfile)가 어떤 강의(Courses)를 어떤 성적으로 이수했는지를
    기록하는 이수 내역 모델
    """
    transcript_id = models.AutoField(primary_key=True)

    # 어떤 사용자의 이수 내역인지 연결
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='transcripts'
    )

    # 어떤 과목을 이수했는지 연결
    course = models.ForeignKey(
        'Courses',
        on_delete=models.PROTECT,  # 이수 내역이 있는 과목 정보는 함부로 삭제되지 않도록 보호
        verbose_name="이수 과목"
    )

    # 해당 과목에서 받은 성적
    grade = models.CharField(max_length=10, help_text="A+, B0, P, F 등")

    class Meta:
        db_table = 'Transcript'
        verbose_name = '사용자 이수 내역'
        verbose_name_plural = '사용자 이수 내역 목록'
        # 한 사용자가 동일한 과목을 중복해서 이수할 수 없도록 제약
        unique_together = (('user_profile', 'course'),)

    def __str__(self):
        return f"{self.user_profile.user.username} - {self.course.course_name} ({self.grade})"


# Graduation_record 테이블 (임시)
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

    def __str__(self):
        return f"{self.user_name or self.user_id} ({self.user_student_id})"


# UserGraduationProgress - 사용자별 졸업요건 진행상황 저장
class UserGraduationProgress(models.Model):
    """
    사용자별 졸업요건 카테고리별 이수 진행상황을 저장하는 모델
    GraduationEngine에서 계산된 결과를 저장하여 시간표 생성 시 활용
    """
    progress_id = models.AutoField(primary_key=True)

    # 사용자 연결
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='graduation_progress'
    )

    # 카테고리 연결 (교양, 전공필수, 전공선택 등)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE
    )

    # 이수 학점
    earned_credits = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="이수 학점"
    )

    # 필요 학점 (졸업요건)
    required_credits = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="필요 학점"
    )

    # 충족 여부
    is_satisfied = models.BooleanField(
        default=False,
        verbose_name="충족 여부"
    )

    # 부족 학점 (계산 필드로 저장)
    shortage_credits = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="부족 학점"
    )

    # 카테고리 레벨 (계층 구조용)
    category_level = models.IntegerField(
        default=0,
        verbose_name="카테고리 레벨"
    )

    # 부모 카테고리 ID (계층 구조용)
    parent_category_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="부모 카테고리 ID"
    )

    # 업데이트 시간
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name="마지막 업데이트"
    )

    class Meta:
        db_table = 'user_graduation_progress'
        verbose_name = '사용자 졸업요건 진행상황'
        verbose_name_plural = '사용자 졸업요건 진행상황 목록'
        unique_together = (('user_profile', 'category'),)
        indexes = [
            models.Index(fields=['user_profile', 'is_satisfied']),
            models.Index(fields=['user_profile', 'shortage_credits']),
        ]

    def __str__(self):
        return f"{self.user_profile.user.username} - {self.category.category_name} ({self.earned_credits}/{self.required_credits})"

    def save(self, *args, **kwargs):
        # 부족 학점 자동 계산
        if self.required_credits is not None and self.required_credits > 0:
            self.shortage_credits = max(0, float(self.required_credits) - float(self.earned_credits))
            self.is_satisfied = self.shortage_credits == 0
        else:
            self.shortage_credits = 0
            # required_credits가 없으면 earned_credits가 있으면 충족으로 간주
            self.is_satisfied = float(self.earned_credits) > 0

        # 카테고리 정보 저장
        if self.category:
            self.category_level = self.category.category_level or 0
            self.parent_category_id = self.category.parent_category_id

        super().save(*args, **kwargs)


# CourseSumm 테이블 - 강의계획서를 통해 요약된 강의 설명 정보 저장
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

    def __str__(self):
        return f"{self.course.course_name} 요약"


# CourseReviewSummary 테이블 - 사용자의 강의평을 요약한 정보 저장
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
                "normal": "보통",  # 사용자의 설명: normal(보통)
                "none": "깐깐함"  # 사용자의 설명: none(깐깐함)
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
                continue  # items_data가 dict가 아니면 건너뛰기

            category_display_label = category_labels.get(category_key, category_key.replace("_", " ").title())

            # 해당 카테고리의 전체 응답 수 계산
            total_count_for_category = sum(items_data.values())

            processed_items = []
            if total_count_for_category > 0:
                for item_key in item_order:  # 정의된 순서대로 처리
                    if item_key in items_data:
                        count = items_data[item_key]
                        item_display_label = item_labels.get(category_key, {}).get(item_key, item_key.title())
                        percentage = (count / total_count_for_category) * 100
                        processed_items.append({
                            'label': item_display_label,
                            'key': item_key,
                            'count': count,
                            'percentage': round(percentage, 1)  # 소수점 첫째 자리까지
                        })

            if processed_items:  # 처리된 항목이 있을 경우에만 추가
                formatted_data.append({
                    'category_label': category_display_label,
                    'items': processed_items,
                    'total_responses': total_count_for_category
                })

        return formatted_data


# UserReview 테이블 - 사용자의 강의평가 정보 저장
class UserReview(models.Model):
    user_review_id = models.AutoField(primary_key=True)
    summary = models.ForeignKey(
        CourseReviewSummary,
        verbose_name="요약 통계",
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    user_profile = models.ForeignKey(
        UserProfile,
        verbose_name="작성자 프로필",
        on_delete=models.CASCADE  # 사용자가 탈퇴하면 강의평도 함께 삭제
    )

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

    def __str__(self):
        return f"{self.summary} / {self.rating}점"


class TranscriptFile(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    original_filename = models.CharField(max_length=255)
    pdf_file = models.FileField(upload_to='transcripts/pdfs/')
    # 모든 이미지 경로와 파싱된 JSON을 저장할 필드들
    original_images = models.JSONField(default=list)
    student_info_image = models.CharField(max_length=255, null=True, blank=True)
    course_history_image = models.CharField(max_length=255, null=True, blank=True)
    credit_summary_image = models.CharField(max_length=255, null=True, blank=True)
    parsed_data = models.JSONField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'TranscriptFile'

    def __str__(self):
        return f"{self.user_profile.user.username} - {self.original_filename}"


# RuleSet (규칙 묶음) 모델
# 특정 학과의 졸업 요건을 저장하는 모델 (ex. 소프트웨어학과 2020년 졸업요건)
class RuleSet(models.Model):
    ruleset_id = models.AutoField(primary_key=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        db_column='department_id'
    )
    ruleset_name = models.CharField(max_length=255, verbose_name="규칙 묶음 이름")
    target_year = models.IntegerField(verbose_name="적용 학년도(입학년도)")
    required_total_credits = models.IntegerField(default=140, verbose_name="요구 총 학점")

    class Meta:
        db_table = 'RuleSet'

    def __str__(self):
        return self.ruleset_name


# Rule (개별 규칙) 모델
# 개별 졸업 요건 (ex. 개신기초교양 9학점 이상)을 저장하는 모델
class Rule(models.Model):
    rule_id = models.AutoField(primary_key=True)
    ruleset = models.ForeignKey(
        RuleSet,
        on_delete=models.CASCADE,
        related_name='rules',
        db_column='ruleset_id'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        db_column='category_id'
    )
    min_credits = models.IntegerField(default=0, verbose_name="최소 이수 학점")
    max_credits = models.IntegerField(null=True, blank=True, verbose_name="최대 인정 학점")
    description = models.CharField(max_length=255, verbose_name="규칙 설명")

    class Meta:
        db_table = 'Rule'

    def __str__(self):
        return f"[{self.ruleset.ruleset_name}] {self.description}"

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
        managed = True

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
        managed = True

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
        managed = True

    def __str__(self):
        return f"{self.timetable_course.course_name} - {self.day_of_week} {self.start_time}-{self.end_time}"