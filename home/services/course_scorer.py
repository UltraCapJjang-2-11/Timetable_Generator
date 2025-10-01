"""
시간표 후보 과목 점수 계산 서비스
졸업요건, 선호도, 평점 등을 기반으로 점수 계산
"""

from typing import List, Dict, Any
from data_manager.models import Courses

from ..views.timetable_types import ScoreCriteria
from ..views.timetable_config import (
    ScoringWeights,
    TAG_FILTERS,
    CLASS_START_HOUR,
    MORNING_END_HOUR
)
from ..utils import get_effective_general_category


class CourseScorer:
    """후보 과목 점수 계산"""

    def calculate_scores(
        self,
        courses: List[Courses],
        criteria: ScoreCriteria
    ) -> None:
        """
        후보 과목들의 점수 계산 (in-place 수정)

        Args:
            courses: 후보 과목 리스트
            criteria: 점수 계산 기준
        """
        for course in courses:
            # 각 점수 계산
            graduation_priority = self._calculate_graduation_priority(course, criteria)
            preference_score = self._calculate_preference_score(course, criteria)
            rating_score = self._calculate_rating_score(course, criteria)

            # 과목 객체에 점수 저장
            course.graduation_priority = graduation_priority
            course.preference_score = preference_score
            course.rating_score = rating_score

            # 디버그 출력
            if preference_score != 0:
                print(f"DEBUG: Course {course.course_name} has preference_score = {preference_score}")
            if rating_score != 0:
                print(f"DEBUG: Course {course.course_name} has rating_score = {rating_score}")

    def _calculate_graduation_priority(
        self,
        course: Courses,
        criteria: ScoreCriteria
    ) -> int:
        """
        졸업요건 기반 우선순위 점수 계산

        Args:
            course: 과목
            criteria: 점수 계산 기준

        Returns:
            졸업요건 우선순위 점수
        """
        priority_score = 0

        # 과목의 카테고리가 미충족 졸업요건에 해당하는지 확인
        if course.category_id in criteria.priority_map:
            priority_score = criteria.priority_map[course.category_id]
            print(f"DEBUG: '{course.course_name}' 졸업요건 우선순위 점수: {priority_score}")

        # 교양 과목이 필요 학점보다 큰 경우 패널티 적용
        if get_effective_general_category(course) and criteria.missing_gen_sub:
            effective_cat = get_effective_general_category(course)
            shortage = criteria.missing_gen_sub.get(effective_cat, 0)
            if shortage > 0 and course.credits > shortage:
                # 초과 학점에 대한 패널티
                penalty = (course.credits - shortage) * ScoringWeights.GENERAL_EXCESS_CREDIT_PENALTY
                priority_score -= penalty
                print(f"DEBUG: '{course.course_name}' 초과 학점 패널티 -{penalty}점 (필요: {shortage}, 실제: {course.credits})")

        # 전공필수 과목에 추가 가중치
        if course.category and course.category.category_name == "전공필수":
            priority_score += ScoringWeights.MAJOR_REQUIRED_BONUS

        return int(priority_score)

    def _calculate_preference_score(
        self,
        course: Courses,
        criteria: ScoreCriteria
    ) -> int:
        """
        선호도 기반 점수 계산

        Args:
            course: 과목
            criteria: 점수 계산 기준

        Returns:
            선호도 점수
        """
        preference_score = 0

        # 선호 교수 확인
        if course.instructor_name:
            if any(prof in course.instructor_name for prof in criteria.preferred_instructors):
                preference_score += ScoringWeights.PREFERRED_INSTRUCTOR_BONUS
                print(f"DEBUG: 선호 교수 매칭 - {course.course_name} ({course.instructor_name}) +{ScoringWeights.PREFERRED_INSTRUCTOR_BONUS}점")

            if any(prof in course.instructor_name for prof in criteria.avoid_instructors):
                preference_score += ScoringWeights.AVOIDED_INSTRUCTOR_PENALTY
                print(f"DEBUG: 기피 교수 매칭 - {course.course_name} ({course.instructor_name}) {ScoringWeights.AVOIDED_INSTRUCTOR_PENALTY}점")

        # 선호 과목 확인
        if any(name.lower() in course.course_name.lower() for name in criteria.preferred_courses):
            preference_score += ScoringWeights.PREFERRED_COURSE_BONUS
            print(f"DEBUG: 선호 과목 매칭 - {course.course_name} +{ScoringWeights.PREFERRED_COURSE_BONUS}점")

        # 교양 과목 태그 필터링
        if get_effective_general_category(course) and criteria.preference_tags:
            tag_matched = False
            for tag in criteria.preference_tags:
                if tag in TAG_FILTERS:
                    if TAG_FILTERS[tag](course.course_name):
                        tag_matched = True
                        preference_score += ScoringWeights.TAG_MATCH_BONUS
                        print(f"DEBUG: 태그 매칭 - {course.course_name} ({tag}) +{ScoringWeights.TAG_MATCH_BONUS}점")
                        break

            # 태그가 선택되었는데 하나도 매칭되지 않으면 선호도 감점
            if not tag_matched:
                preference_score += ScoringWeights.TAG_MISMATCH_PENALTY

        # 시간대 선호도
        if criteria.prefer_morning or criteria.prefer_afternoon:
            schedules = course.courseschedule_set.all()
            morning_count = 0
            afternoon_count = 0

            for sch in schedules:
                times = [int(t) + CLASS_START_HOUR for t in sch.times.split(',') if t.strip().isdigit()]
                for hour in times:
                    if hour < MORNING_END_HOUR:
                        morning_count += 1
                    else:
                        afternoon_count += 1

            # 시간대 선호도 비율 기반 점수
            total_hours = morning_count + afternoon_count
            if total_hours > 0:
                if criteria.prefer_morning:
                    morning_ratio = morning_count / total_hours
                    bonus = int(morning_ratio * ScoringWeights.MORNING_PREFERENCE_BONUS)
                    preference_score += bonus
                    print(f"DEBUG: 오전 선호 - {course.course_name} 오전비율 {morning_ratio:.1%} +{bonus}점")
                elif criteria.prefer_afternoon:
                    afternoon_ratio = afternoon_count / total_hours
                    bonus = int(afternoon_ratio * ScoringWeights.AFTERNOON_PREFERENCE_BONUS)
                    preference_score += bonus
                    print(f"DEBUG: 오후 선호 - {course.course_name} 오후비율 {afternoon_ratio:.1%} +{bonus}점")

        return preference_score

    def _calculate_rating_score(
        self,
        course: Courses,
        criteria: ScoreCriteria
    ) -> int:
        """
        평점 기반 점수 계산

        Args:
            course: 과목
            criteria: 점수 계산 기준

        Returns:
            평점 점수
        """
        rating_score = 0
        review_key = (course.course_name, course.instructor_name)

        if review_key in criteria.review_summaries and review_key[0] and review_key[1]:
            avg_rating = float(criteria.review_summaries[review_key].avg_rating)

            # 평점 구간별 점수 부여
            if avg_rating >= 4.5:
                rating_score = ScoringWeights.RATING_4_5_PLUS
            elif avg_rating >= 4.0:
                rating_score = ScoringWeights.RATING_4_0_PLUS
            elif avg_rating >= 3.5:
                rating_score = ScoringWeights.RATING_3_5_PLUS
            elif avg_rating >= 3.0:
                rating_score = ScoringWeights.RATING_3_0_PLUS
            else:
                rating_score = ScoringWeights.RATING_BELOW_3_0

            print(f"DEBUG: 평점 적용 - {course.course_name} ({course.instructor_name}) 평점 {avg_rating:.2f} → +{rating_score}점")

        return rating_score

    def calculate_timetable_preference_score(
        self,
        timetable: List[Dict[str, Any]],
        criteria: ScoreCriteria
    ) -> tuple[int, Dict[str, int]]:
        """
        시간표의 선호도 점수 계산

        Args:
            timetable: 시간표 (과목 리스트)
            criteria: 점수 계산 기준

        Returns:
            (점수, 매칭 정보) 튜플
        """
        score = 0
        matched_prefs = {'instructors': 0, 'courses': 0, 'avoided': 0}

        for course in timetable:
            instructor = course.get('instructor_name', '')
            course_name = course.get('course_name', '')

            # 선호 교수 점수
            if instructor and criteria.preferred_instructors:
                for pref in criteria.preferred_instructors:
                    if pref in instructor:
                        score += ScoringWeights.PREFERRED_INSTRUCTOR_BONUS
                        matched_prefs['instructors'] += 1
                        print(f"  DEBUG: 선호 교수 매칭 +{ScoringWeights.PREFERRED_INSTRUCTOR_BONUS}: {course_name} ({instructor})")

            # 기피 교수 감점
            if instructor and criteria.avoid_instructors:
                for avoid in criteria.avoid_instructors:
                    if avoid in instructor:
                        score += ScoringWeights.AVOIDED_INSTRUCTOR_PENALTY
                        matched_prefs['avoided'] += 1
                        print(f"  DEBUG: 기피 교수 발견 {ScoringWeights.AVOIDED_INSTRUCTOR_PENALTY}: {course_name} ({instructor})")

            # 선호 과목 점수
            if criteria.preferred_courses:
                for pref in criteria.preferred_courses:
                    if pref.lower() in course_name.lower():
                        score += ScoringWeights.PREFERRED_COURSE_BONUS
                        matched_prefs['courses'] += 1
                        print(f"  DEBUG: 선호 과목 매칭 +{ScoringWeights.PREFERRED_COURSE_BONUS}: {course_name}")

            # 기피 과목 감점
            if criteria.avoid_courses:
                for avoid in criteria.avoid_courses:
                    if avoid.lower() in course_name.lower():
                        score += ScoringWeights.AVOIDED_COURSE_PENALTY
                        matched_prefs['avoided'] += 1
                        print(f"  DEBUG: 기피 과목 발견 {ScoringWeights.AVOIDED_COURSE_PENALTY}: {course_name}")

            # 시간대 선호도
            if criteria.prefer_morning or criteria.prefer_afternoon:
                schedules = course.get('schedules', [])
                morning_count = 0
                afternoon_count = 0

                for sch in schedules:
                    times = sch.get('times', '')
                    if times:
                        for t in times.split(','):
                            if t.strip().isdigit():
                                hour = int(t) + CLASS_START_HOUR
                                if hour < MORNING_END_HOUR:
                                    morning_count += 1
                                else:
                                    afternoon_count += 1

                if criteria.prefer_morning and morning_count > afternoon_count:
                    score += ScoringWeights.TIME_SLOT_PREFERENCE_BONUS
                elif criteria.prefer_afternoon and afternoon_count > morning_count:
                    score += ScoringWeights.TIME_SLOT_PREFERENCE_BONUS

        return score, matched_prefs

    def get_recommendation_level(self, score: int) -> str:
        """
        점수에 따른 추천 레벨 반환

        Args:
            score: 선호도 점수

        Returns:
            추천 레벨 (별점 문자열)
        """
        from ..views.timetable_config import RECOMMENDATION_LEVELS

        for level_name, (stars, threshold) in RECOMMENDATION_LEVELS.items():
            if score > threshold:
                return stars

        return '★'
