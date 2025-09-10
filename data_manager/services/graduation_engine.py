# your_app/engine/graduation_engine.py

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from django.conf import settings
from django.db.models import Max
from data_manager.models import Category, Rule, RuleSet  # 필요한 모델들을 가져옵니다.
from .graduation_types import RuleResult


# --- 졸업 판별 엔진 ---
class GraduationEngine:
    """
    졸업 요건 판별 엔진 (Phase 1, 2, 3 구현 완료)
    """
    # 클래스 변수로써, 한번 로드된 설정/데이터를 메모리에 캐싱하여 성능을 최적화
    _DEPARTMENT_GROUPS_MAP = None
    _CATEGORIES_CACHE = {}

    def __init__(self, user_profile, transcripts):
        """Phase 2: 엔진 실행 및 초기화"""
        self.user_profile = user_profile
        self.transcripts = transcripts
        self.ruleset = getattr(user_profile, 'rule_set', None)

        self.department_groups = self._load_department_groups()

        self.categories_map = {}
        self.effective_year = None

        # 규칙셋 기준년도 우선, 없으면 입학년도로 카테고리 버전 결정
        # 주어진 연도보다 작거나 같은 최신 카테고리 버전으로 매핑
        if self.ruleset and getattr(self.ruleset, 'target_year', None):
            self.effective_year = self._get_effective_version_year(self.ruleset.target_year)
        elif getattr(self.user_profile, 'admission_year', None):
            self.effective_year = self._get_effective_version_year(self.user_profile.admission_year)

        if self.effective_year:
            self.categories_map = self._load_category(self.effective_year)
            # 폴백: 해당 연도의 카테고리가 없으면 가장 최신 버전으로 로드
            if not self.categories_map:
                latest = Category.objects.aggregate(Max('version_year'))['version_year__max']
                if latest:
                    self.effective_year = latest
                    self.categories_map = self._load_category(self.effective_year)

        self.processed_data = {
            'total_credits': 0.0,
            'credits_by_category': defaultdict(float),
        }

        # Phase 3: 데이터 사전 처리 실행
        self._preprocess_data()

        print(f"GraduationEngine for {user_profile.user.username} initialized.")

    @classmethod
    def _get_effective_version_year(cls, admission_year):
        """학생의 입학년도를 기준으로, 적용할 가장 최신의 카테고리 기준년도를 찾습니다."""
        try:
            result = Category.objects.filter(version_year__lte=admission_year).aggregate(Max('version_year'))
            return result['version_year__max']
        except Exception as e:
            print(f"유효 기준년도 조회 중 오류 발생: {e}")
            return None

    @classmethod
    def _load_department_groups(cls):
        """department_groups.json 파일을 읽어, 역방향 맵으로 변환 후 캐싱합니다."""
        if cls._DEPARTMENT_GROUPS_MAP is None:
            file_path = os.path.join(settings.BASE_DIR, 'config', 'department_groups.json')
            inverted_map = {}
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    readable_groups = json.load(f)
                    for group_name, department_list in readable_groups.items():
                        for department_name in department_list:
                            inverted_map[department_name] = group_name
                    cls._DEPARTMENT_GROUPS_MAP = inverted_map
            except FileNotFoundError:
                cls._DEPARTMENT_GROUPS_MAP = {}
        return cls._DEPARTMENT_GROUPS_MAP

    @classmethod
    def _load_category(cls, target_year):
        """특정 연도의 카테고리 전체를 DB에서 조회하여 캐시에 저장합니다."""
        if target_year not in cls._CATEGORIES_CACHE:
            categories = Category.objects.filter(version_year=target_year)
            category_map = {cat.category_id: cat for cat in categories}
            cls._CATEGORIES_CACHE[target_year] = category_map
        return cls._CATEGORIES_CACHE[target_year]

    def _get_root_category(self, category_obj):
        """
        주어진 카테고리 객체로부터 최상위 부모 카테고리를 찾아 반환합니다.
        메모리에 캐싱된 self.categories_map을 사용하므로 DB 조회가 발생하지 않습니다.
        """
        current_cat = category_obj
        while current_cat and current_cat.parent_category_id:
            parent_cat = self.categories_map.get(current_cat.parent_category_id)
            if not parent_cat: # 부모를 찾을 수 없으면 현재 카테고리가 최상위
                break
            current_cat = parent_cat
        return current_cat

    def _preprocess_data(self):
        """[수정] 모든 과목 유형을 고려하여 데이터를 사전 처리합니다."""
        PASS_GRADES = ['A+', 'A0', 'A-', 'B+', 'B0', 'B-', 'C+', 'C0', 'C-', 'P', '미입력']

        general_elective_category = None
        if self.categories_map:
            for cat in self.categories_map.values():
                if cat.category_name == '일반선택':  # '일반선택'은 '일선'의 다른 이름일 수 있으니 확인 필요
                    general_elective_category = cat
                    break

        for transcript in self.transcripts:
            if transcript.grade not in PASS_GRADES:
                continue

            course = transcript.course
            credits = float(course.credits)
            self.processed_data['total_credits'] += credits

            effective_category = None  # 이번 과목에 적용될 최종 카테고리


            # 1. 과목의 최상위 카테고리를 먼저 확인
            root_category = self._get_root_category(course.category)

            # 루트 카테고리 명칭 정규화(동의어 포함)
            root_name = root_category.category_name if root_category else None
            root_matches = {'교양', '교직', '일선', '일반선택'}
            if root_name in root_matches:
                # 과목 자체가 교양, 교직, 일선인 경우, 그대로 인정
                effective_category = course.category

            elif course.dept is None:
                # 학과 정보가 없는 과목은 '일반선택'으로 처리
                effective_category = general_elective_category

            else:
                # 전공 과목들만 학생과의 관계를 따짐
                student_dept_name = getattr(self.user_profile.department, 'dept_name', None)
                course_dept_name = getattr(course.dept, 'dept_name', None)

                student_group = self.department_groups.get(student_dept_name)
                course_group = self.department_groups.get(course_dept_name)

                if student_group and student_group == course_group:
                    # 우리 학과(그룹)의 전공 수업일 경우
                    effective_category = course.category

                else:
                    # 타과의 전공 수업일 경우
                    effective_category = general_elective_category


            # 계층적 학점 누적 (이 부분은 수정 없음)
            if effective_category:
                current_category = effective_category
                while current_category:
                    self.processed_data['credits_by_category'][current_category.category_id] += credits
                    parent_id = current_category.parent_category_id
                    if not parent_id:
                        break
                    current_category = self.categories_map.get(parent_id)

    def _evaluate_rule(self, rule: Rule) -> RuleResult:
        """
        Phase 4: 단일 규칙을 평가하여 그 결과를 RuleResult 객체로 반환합니다.
        """
        category = rule.category
        current_credits = self.processed_data['credits_by_category'].get(category.category_id, 0.0)
        is_satisfied = (current_credits >= rule.min_credits)
        remark = ""
        if not is_satisfied:
            shortage = rule.min_credits - current_credits
            remark = f"{category.category_name} - {int(shortage)}학점 부족"

        return RuleResult(
            rule_description=rule.description,
            category_name=category.category_name,
            required_credits=rule.min_credits,
            earned_credits=current_credits,
            is_satisfied=is_satisfied,
            remark=remark
        )

    def run(self) -> list[RuleResult]:
        """
        Phase 5: RuleSet의 모든 규칙을 평가하고, 그 결과들을 RuleResult 객체 리스트로 최종 반환합니다.
        """
        results: list[RuleResult] = []

        if not self.ruleset:
            print("경고: 해당 사용자에게 할당된 졸업요건(RuleSet)이 없습니다.")
            return results

        rules_to_evaluate = self.ruleset.rules.select_related('category').all().order_by('pk')

        for rule in rules_to_evaluate:
            result = self._evaluate_rule(rule)
            results.append(result)
        print("dd")
        print(json.dump(results, indent=4, ensure_ascii=False))
        
        return results