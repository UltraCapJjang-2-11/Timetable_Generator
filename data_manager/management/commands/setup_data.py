import json
import csv
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction

# 1. 모델 임포트 (your_app을 실제 앱 이름으로 변경하세요)
from data_manager.models import (
    University, College, Department, Major,
    Semester, Category, Courses, CourseSchedule, RuleSet, Rule,
    CourseReviewSummary, UserReview, UserProfile, CourseSumm
)

DATA_DIR = Path(__file__).parent / 'setup_data'


class Command(BaseCommand):
    help = 'JSON과 CSV 파일들을 사용하여 데이터베이스 초기 데이터를 셋업합니다.'

    def add_arguments(self, parser):
        """커맨드에 옵션을 추가합니다."""
        parser.add_argument(
            '--clear',
            action='store_true',
            help='DB의 관련 테이블 데이터를 모두 삭제한 후 셋업을 시작합니다.'
        )

    def _safe_to_int(self, value, default=0):
        """문자열을 안전하게 정수형으로 변환합니다. 빈 문자열이나 None이면 기본값을 반환합니다."""
        if value in (None, ''):
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default

    def _safe_to_float(self, value, default=0.0):
        """문자열을 안전하게 실수형으로 변환합니다. 빈 문자열이나 None이면 기본값을 반환합니다."""
        if value in (None, ''):
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    @transaction.atomic
    def handle(self, *args, **options):
        """메인 핸들러: 정의된 순서에 따라 데이터 셋업 함수들을 호출합니다."""

        if options['clear']:
            self._clear_database()

        self.stdout.write(self.style.SUCCESS("🚀 데이터베이스 셋업을 시작합니다..."))

        if not DATA_DIR.is_dir():
            self.stdout.write(self.style.ERROR(f"오류: 데이터 디렉토리를 찾을 수 없습니다. '{DATA_DIR}' 경로를 확인해주세요."))
            return

        self.setup_university_structure(DATA_DIR / "list.json")
        self.setup_semesters(DATA_DIR / "semester.csv")
        self.setup_categories(DATA_DIR / "category.json")
        self.setup_courses_and_schedules(DATA_DIR / "course_list_result.csv")
        self.setup_rulesets_and_rules(DATA_DIR / "graduation_rules.json")
        self.setup_course_review_summaries(DATA_DIR / "course_review_summaries.csv")
        # self.setup_course_summs(DATA_DIR / "course_summ.csv")

        self.stdout.write(self.style.SUCCESS("🎉 모든 데이터 셋업이 성공적으로 완료되었습니다!"))

    def _clear_database(self):
        """관련 테이블의 모든 데이터를 삭제합니다."""
        self.stdout.write(self.style.WARNING("⚠️  --clear 옵션이 감지되었습니다. 기존 데이터를 삭제합니다..."))

        models_to_clear = [
            CourseSumm, UserReview, CourseReviewSummary,  # 새로 추가 (순서 중요)
            CourseSchedule, Courses, Category, Semester,
            Major, Department, College, University, RuleSet, Rule
        ]

        for model in models_to_clear:
            model_name = model.__name__
            deleted_count, _ = model.objects.all().delete()
            self.stdout.write(f"  - {model_name} 테이블 데이터 삭제 완료 ({deleted_count}개)")

        self.stdout.write(self.style.SUCCESS("  ✓ 모든 관련 테이블이 초기화되었습니다."))

    def setup_university_structure(self, file_path):
        """1-4단계: 대학, 단과대학, 학과, 전공 정보 셋업"""
        self.stdout.write(self.style.NOTICE("  - 1-4단계: 대학/학과/전공 구조 셋업 중..."))

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        university, _ = University.objects.get_or_create(university_name=data['university_name'])

        for college_data in data['colleges']:
            college, _ = College.objects.get_or_create(
                university=university,
                college_name=college_data['college_name']
            )
            for dept_data in college_data['departments']:
                department, _ = Department.objects.get_or_create(
                    university=university,
                    college=college,
                    dept_name=dept_data['dept_name']
                )
                for major_name in dept_data.get('majors', []):
                    Major.objects.get_or_create(dept=department, major_name=major_name)
        self.stdout.write(self.style.SUCCESS("  ✓ 완료"))

    def setup_semesters(self, file_path):
        """5단계: 학기 정보 셋업"""
        self.stdout.write(self.style.NOTICE("  - 5단계: 학기 정보 셋업 중..."))
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                Semester.objects.get_or_create(
                    year=row[1],
                    term=row[2],
                    defaults={
                        'start_date': row[3],
                        'end_date': row[4],
                        'course_registration_start': row[5],
                        'course_registration_end': row[6],
                    }
                )
        self.stdout.write(self.style.SUCCESS("  ✓ 완료"))

    def setup_categories(self, file_path):
        """6단계: 이수 구분 카테고리 정보 셋업"""
        self.stdout.write(self.style.NOTICE("  - 6단계: 이수 구분 카테고리 정보 셋업 중..."))
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        version_year = data['version_year']
        for category_data in data['categories']:
            self._create_category_recursive(category_data, version_year)
        self.stdout.write(self.style.SUCCESS("  ✓ 완료"))

    def _create_category_recursive(self, category_data, year, parent=None):
        """setup_categories의 재귀 헬퍼 함수"""
        category, _ = Category.objects.get_or_create(
            category_name=category_data['category_name'],
            version_year=year,
            parent_category=parent,
            defaults={'category_level': category_data['category_level']}
        )
        for child_data in category_data.get('children', []):
            self._create_category_recursive(child_data, year, parent=category)

    def _parse_schedule(self, raw_time):
        """
        예: "월 02 ,03 [S4-1-101(21-101)]  목 01 [S4-1-101(21-101)]"
        파싱 →
        [
          {"day": "월", "times": ["02", "03"], "location": "S4-1-101(21-101)"},
          {"day": "목", "times": ["01"],       "location": "S4-1-101(21-101)"}
        ]
        """
        if not raw_time or not isinstance(raw_time, str):
            return []
        pattern = r"([월화수목금토일])\s+([\d,\s]+)\s*\[([^\]]+)\]"
        matches = re.findall(pattern, raw_time)
        result = []
        for day, time_str, location in matches:
            times = [t.strip() for t in time_str.split(',') if t.strip()]
            result.append({
                "day": day,
                "times": times,
                "location": location
            })
        return result

    def setup_courses_and_schedules(self, file_path):
        """7단계: 강의 및 시간표 정보 셋업"""
        self.stdout.write(self.style.NOTICE("  - 7단계: 강의 및 시간표 정보 셋업 중..."))

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    semester_obj = Semester.objects.get(year=row['offered_year'], term=row['semester'])

                    category_obj = None
                    version_year = row['offered_year']

                    if row['category1'] == '전공':
                        category_obj = Category.objects.get(category_name=row['category_raw'])
                    elif row['category1'] == '교양' and row.get('field'):
                        category_obj = Category.objects.get(category_name=row['field'])
                    else:
                        category_obj = Category.objects.get(category_name=row['category1'])

                    dept_obj, major_obj = None, None
                    if row.get('department'):
                        dept_name = row['department']
                        dept_obj = Department.objects.get(dept_name=dept_name)
                        if row.get('_major'):
                            major_name = row['_major']
                            major_obj = Major.objects.get(major_name=major_name, dept=dept_obj)

                    course_obj, created = Courses.objects.get_or_create(
                        course_code=row['course_code'],
                        semester=semester_obj,
                        section=row['section'],
                        defaults={
                            'dept': dept_obj,
                            'major': major_obj,
                            'category': category_obj,
                            'course_name': row['course_name'],
                            'credits': self._safe_to_int(row.get('credits')),
                            'target_year': row.get('target_year', ''),
                            'grade_type': row.get('grade_type', ''),
                            'foreign_course': row.get('foreign_course'),
                            'instructor_name': row.get('instructor_name'),
                            'lecture_hours': self._safe_to_float(row.get('lecture_hours')),
                            'lecture_times': self._safe_to_float(row.get('lecture_times')),
                            'lab_hours': self._safe_to_float(row.get('lab_hours')),
                            'lab_times': self._safe_to_float(row.get('lab_times')),
                            'pre_enrollment_count': self._safe_to_int(row.get('pre_enrollment_count')),
                            'capacity': self._safe_to_int(row.get('capacity')),
                            'enrolled_count': self._safe_to_int(row.get('enrolled_count')),
                        }
                    )

                    # --- CourseSchedule 저장 ---
                    schedules = self._parse_schedule(row.get('schedule_raw'))
                    for schedule_info in schedules:
                        # get_or_create 대신 update_or_create 사용
                        CourseSchedule.objects.update_or_create(
                            course=course_obj,
                            day=schedule_info['day'],
                            defaults={
                                'times': ','.join(schedule_info['times']),
                                'location': schedule_info['location'],
                            }
                        )

                except Department.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"  !! 학과 없음 (과목코드: {row.get('course_code')}): DB에 '{row.get('department')}' 학과가 없습니다. list.json 파일을 확인하세요."))
                except Major.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"  !! 전공 없음 (과목코드: {row.get('course_code')}): '{row.get('department')}' 학과에 '{row.get('_major')}' 전공이 없습니다. list.json 파일을 확인하세요."))
                except Category.DoesNotExist as e:
                    self.stdout.write(self.style.WARNING(
                        f"  !! 카테고리 없음 (과목코드: {row.get('course_code')}): {e}. category.json 파일을 확인하세요."))
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  !! 알 수 없는 오류 (과목코드: {row.get('course_code')}): {e}. 해당 행을 건너뜁니다."))
                    continue
        self.stdout.write(self.style.SUCCESS("  ✓ 완료"))

    def setup_rulesets_and_rules(self, file_path):
        self.stdout.write(self.style.NOTICE("  - 8단계: 졸업 요건 데이터 셋업 중..."))

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                rulesets_data = data.get('rulesets', [])

                for rs_data in rulesets_data:
                    dept = Department.objects.get(dept_name=rs_data['department_name'])
                    ruleset, created = RuleSet.objects.get_or_create(
                        ruleset_name=rs_data['ruleset_name'],
                        department=dept,
                        target_year=rs_data['target_year'],
                        defaults = {
                            'required_total_credits': rs_data.get('required_total_credits', 140)
                        }
                    )

                    for rule_data in rs_data.get('rules', []):
                        cat = Category.objects.get(category_name=rule_data['category_name'])
                        Rule.objects.get_or_create(
                            ruleset=ruleset,
                            category=cat,
                            description=rule_data['description'],
                            defaults={
                                'min_credits': rule_data['min_credits'],
                                'max_credits': rule_data.get('max_credits')
                            }
                        )
            self.stdout.write(self.style.SUCCESS("  ✓ 완료"))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('graduation_rules.json 가 존재하지 않습니다.'))

    def setup_course_review_summaries(self, file_path):
        """강의 리뷰 요약 정보 및 개별 리뷰 셋업"""
        self.stdout.write(self.style.NOTICE("  - 9단계: 강의 리뷰 요약 정보 및 개별 리뷰 셋업 중..."))

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    dist_json = json.loads(row['dist_json']) if row.get('dist_json') else {}

                    # CourseReviewSummary 생성
                    summary, created = CourseReviewSummary.objects.update_or_create(
                        course_code=row['course_code'],
                        instructor_name=row['instructor_name'],
                        defaults={
                            'course_name': row['course_name'],
                            'review_count': self._safe_to_int(row.get('review_count', 0)),
                            'avg_rating': self._safe_to_float(row.get('avg_rating', 0)),
                            'dist_json': dist_json,
                            'review_sum': row.get('review_sum', ''),
                        }
                    )

                    # user_reviews 컬럼이 있으면 UserReview 생성
                    if 'user_reviews' in row and row['user_reviews']:
                        try:
                            user_reviews = json.loads(row['user_reviews'])
                            for review in user_reviews:
                                UserReview.objects.update_or_create(
                                    summary=summary,
                                    semester=review.get('semester', ''),
                                    comment_text=review.get('text', ''),
                                    defaults={
                                        'rating': self._safe_to_float(review.get('star', 0)),
                                        'user_profile': None,  # 익명 처리
                                        'is_anonymous': True,
                                    }
                                )
                        except json.JSONDecodeError as e:
                            self.stdout.write(self.style.WARNING(
                                f"  !! user_reviews JSON 파싱 오류 (과목: {row.get('course_code')}): {e}"))

                except json.JSONDecodeError as e:
                    self.stdout.write(self.style.WARNING(
                        f"  !! JSON 파싱 오류 (과목: {row.get('course_code')}): {e}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"  !! 오류 (과목: {row.get('course_code')}): {e}"))

        self.stdout.write(self.style.SUCCESS("  ✓ 완료"))


    def setup_course_summs(self, file_path):
        """강의 요약 정보 셋업 (CourseSumm)"""
        self.stdout.write(self.style.NOTICE("  - 강의 요약 정보 (CourseSumm) 셋업 중..."))

        # Courses 캐싱 (성능 최적화)
        courses_cache = {}

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    year = self._safe_to_int(row['year'])
                    term = row['term']
                    course_code = row['course_code']
                    section = row['section']

                    # 캐시 키 생성
                    cache_key = f"{year}_{term}_{course_code}_{section}"

                    # 캐시에서 찾거나 DB에서 조회
                    if cache_key not in courses_cache:
                        semester = Semester.objects.get(year=year, term=term)
                        course = Courses.objects.get(
                            semester=semester,
                            course_code=course_code,
                            section=section
                        )
                        courses_cache[cache_key] = course
                    else:
                        course = courses_cache[cache_key]

                    # CourseSumm 생성 또는 업데이트
                    CourseSumm.objects.update_or_create(
                        course=course,
                        defaults={
                            'course_summarization': row.get('course_summarization', ''),
                            'group_activity': row.get('group_activity', 'N'),
                        }
                    )

                except Semester.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"  !! Semester 없음: {row.get('year')} {row.get('term')}"))
                except Courses.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"  !! Course 없음: {row.get('course_code')} (분반: {row.get('section')}, 학기: {row.get('year')} {row.get('term')})"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"  !! 오류 (과목코드: {row.get('course_code')}): {e}"))

        self.stdout.write(self.style.SUCCESS("  ✓ 완료"))
