from typing import Optional, Tuple

from django.db import transaction

from data_manager.models import (
    UserProfile,
    College,
    Department,
    RuleSet,
)


class UserProfileService:
    """
    UserProfile 관련 CRUD 및 부가 로직(규칙셋 자동 할당) 서비스
    """

    @staticmethod
    def _get_college_by_name(college_name: Optional[str]) -> Optional[College]:
        if not college_name:
            return None
        try:
            return College.objects.get(college_name=college_name)
        except College.DoesNotExist:
            return None

    @staticmethod
    def _get_department_by_name(department_name: Optional[str]) -> Optional[Department]:
        if not department_name:
            return None
        try:
            return Department.objects.get(dept_name=department_name)
        except Department.DoesNotExist:
            return None

    @staticmethod
    def _assign_ruleset_by_department_and_year(
        department: Optional[Department], target_year: Optional[int]
    ) -> Optional[RuleSet]:
        if not department or not target_year:
            return None
        try:
            return RuleSet.objects.filter(department=department, target_year=target_year).first()
        except Exception:
            return None

    @transaction.atomic
    def update_academic_info(
        self,
        user_profile: UserProfile,
        *,
        user_name: Optional[str],
        user_student_id: Optional[str],
        college_name: Optional[str],
        department_name: Optional[str],
        admission_year: Optional[int],
        current_grade: Optional[int],
        completed_semesters: Optional[int],
    ) -> Tuple[UserProfile, Optional[RuleSet]]:
        """
        사용자 학사 정보를 UserProfile에 반영하고, (department, admission_year)에 따라 RuleSet을 할당합니다.
        반환: (갱신된 UserProfile, 할당된 RuleSet 또는 None)
        """
        college = self._get_college_by_name(college_name)
        department = self._get_department_by_name(department_name)

        user_profile.college = college
        user_profile.department = department

        # 선택 필드들만 값이 주어진 경우에 갱신
        if user_name is not None:
            user_profile.user_name = user_name
        if user_student_id is not None:
            user_profile.user_student_id = user_student_id
        if admission_year is not None:
            user_profile.admission_year = admission_year
        if current_grade is not None:
            user_profile.current_grade = current_grade
        if completed_semesters is not None:
            user_profile.completed_semesters = completed_semesters

        # 규칙셋 자동 할당(없으면 None 유지)
        ruleset = self._assign_ruleset_by_department_and_year(department, admission_year)
        user_profile.rule_set = ruleset

        # 온보딩 상태 업데이트(정보 확인 완료)
        try:
            user_profile.onboarding_status = 'INFO_CONFIRMED'
        except Exception:
            # 필드가 없거나 설정 실패해도 흐름을 막지 않음
            pass

        user_profile.save()

        return user_profile, ruleset


