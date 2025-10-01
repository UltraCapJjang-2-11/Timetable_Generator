"""
시간표 생성 요청 파라미터 파싱 서비스
Django request에서 시간표 생성에 필요한 모든 파라미터를 추출 및 검증
"""

import json
from typing import Dict, List, Any
from django.http import HttpRequest

from ..views.timetable_types import TimetableRequest
from ..views.timetable_config import (
    MIN_CREDITS, MAX_CREDITS,
    MAX_MAJOR_CREDITS, MAX_ELECTIVE_CREDITS,
    DEFAULT_TOTAL_CREDITS, DEFAULT_MAJOR_CREDITS, DEFAULT_ELECTIVE_CREDITS,
    ValidationMessages
)


class ParameterParser:
    """시간표 생성 요청 파라미터 파싱"""

    def parse_request(self, request: HttpRequest) -> TimetableRequest:
        """
        Django 요청에서 시간표 생성 파라미터 추출

        Args:
            request: Django HttpRequest 객체

        Returns:
            TimetableRequest 데이터클래스 인스턴스

        Raises:
            ValueError: 파라미터가 올바르지 않을 경우
        """
        # 기본 파라미터 추출
        params = TimetableRequest(
            # 학점
            target_total=self._parse_credits(request, 'total_credits', DEFAULT_TOTAL_CREDITS),
            target_major=self._parse_credits(request, 'major_credits', DEFAULT_MAJOR_CREDITS),
            target_elective=self._parse_credits(request, 'elective_credits', DEFAULT_ELECTIVE_CREDITS),

            # 공강 및 과목 관련
            free_days=request.GET.getlist('free_days[]'),
            existing_courses=self._parse_int_list(request.GET.getlist('existing_courses[]')),
            exclude_courses=request.GET.getlist('exclude_courses[]'),
            required_courses=request.GET.getlist('required_courses[]'),

            # 선호도
            preferred_instructors=request.GET.getlist('preferred_instructors[]'),
            avoid_instructors=request.GET.getlist('avoid_instructors[]'),
            preferred_courses=request.GET.getlist('preferred_courses[]'),
            avoid_courses=request.GET.getlist('avoid_courses[]'),

            # 교양 태그
            preference_tags=request.GET.getlist('preference_tags[]'),

            # 시간대 선호
            prefer_morning=request.GET.get('prefer_morning', 'false').lower() == 'true',
            prefer_afternoon=request.GET.get('prefer_afternoon', 'false').lower() == 'true',
            prefer_compact=request.GET.get('prefer_compact', 'false').lower() == 'true',

            # 건물 거리
            max_walking_time=int(request.GET.get('max_walking_time', 10)),

            # 시간 제약 조건
            only_time_ranges=self._parse_json_list(request.GET.getlist('only_time_ranges[]')),
            avoid_times=self._parse_json_list(request.GET.getlist('avoid_times[]')),
            avoid_time_ranges=self._parse_json_list(request.GET.getlist('avoid_time_ranges[]')),
            specific_avoid_times=self._parse_json_list(request.GET.getlist('specific_avoid_times[]')),
            specific_avoid_time_ranges=self._parse_json_list(request.GET.getlist('specific_avoid_time_ranges[]')),
        )

        # 학점 검증 및 조정
        self._validate_and_adjust_credits(params)

        # 디버그 출력
        self._print_parsed_params(params)

        return params

    def _parse_credits(self, request: HttpRequest, key: str, default: int) -> int:
        """학점 파라미터 파싱"""
        try:
            return int(request.GET.get(key, default))
        except ValueError:
            raise ValueError(ValidationMessages.INVALID_CREDITS)

    def _parse_int_list(self, str_list: List[str]) -> List[int]:
        """문자열 리스트를 정수 리스트로 변환"""
        result = []
        for item in str_list:
            try:
                result.append(int(item))
            except ValueError:
                continue
        return result

    def _parse_json_list(self, json_list: List[str]) -> List[Dict[str, Any]]:
        """JSON 문자열 리스트를 딕셔너리 리스트로 변환"""
        result = []
        for json_str in json_list:
            try:
                result.append(json.loads(json_str))
            except json.JSONDecodeError:
                continue
        return result

    def _validate_and_adjust_credits(self, params: TimetableRequest) -> None:
        """
        학점 검증 및 조정

        Args:
            params: TimetableRequest 객체 (in-place 수정)

        Raises:
            ValueError: 학점 파라미터가 올바르지 않을 경우
        """
        # 학점 범위 검증
        if params.target_total < MIN_CREDITS or params.target_total > MAX_CREDITS:
            print(f"DEBUG: {ValidationMessages.ABNORMAL_TOTAL_CREDITS}: {params.target_total}")
            params.target_total = min(max(params.target_total, MIN_CREDITS), MAX_CREDITS)

        if params.target_major < MIN_CREDITS or params.target_major > MAX_MAJOR_CREDITS:
            print(f"DEBUG: {ValidationMessages.ABNORMAL_MAJOR_CREDITS}: {params.target_major}")
            params.target_major = min(max(params.target_major, MIN_CREDITS), MAX_MAJOR_CREDITS)

        if params.target_elective < MIN_CREDITS or params.target_elective > MAX_ELECTIVE_CREDITS:
            print(f"DEBUG: {ValidationMessages.ABNORMAL_ELECTIVE_CREDITS}: {params.target_elective}")
            params.target_elective = min(max(params.target_elective, MIN_CREDITS), MAX_ELECTIVE_CREDITS)

        # 전공 + 교양 학점이 총 학점을 초과하지 않도록 조정
        if params.target_major + params.target_elective > params.target_total:
            # 비율에 따라 조정
            ratio = params.target_total / (params.target_major + params.target_elective)
            params.target_major = int(params.target_major * ratio)
            params.target_elective = params.target_total - params.target_major
            print(f"DEBUG: {ValidationMessages.CREDITS_ADJUSTED.format(major=params.target_major, elective=params.target_elective)}")

        # 실제 목표 학점을 전공 + 교양 학점의 합으로 설정
        actual_total = params.target_major + params.target_elective
        if actual_total != params.target_total:
            print(f"DEBUG: {ValidationMessages.ACTUAL_CREDITS_ADJUSTED.format(requested=params.target_total, actual=actual_total)}")
            params.target_total = actual_total

    def _print_parsed_params(self, params: TimetableRequest) -> None:
        """파싱된 파라미터 디버그 출력"""
        print("DEBUG: --- Parsed Parameters ---")
        print(f"  학점: total={params.target_total}, major={params.target_major}, elective={params.target_elective}")
        print(f"  공강 요일: {params.free_days}")
        print(f"  필수 과목: {params.required_courses}")
        print(f"  제외 과목: {params.exclude_courses}")
        print(f"  선호 교수: {params.preferred_instructors}")
        print(f"  기피 교수: {params.avoid_instructors}")
        print(f"  선호 과목: {params.preferred_courses}")
        print(f"  기피 과목: {params.avoid_courses}")
        print(f"  교양 태그: {params.preference_tags}")
        print(f"  시간대 선호: morning={params.prefer_morning}, afternoon={params.prefer_afternoon}, compact={params.prefer_compact}")
        print(f"  최대 이동시간: {params.max_walking_time}분")
        print(f"  시간 제약: only_ranges={len(params.only_time_ranges)}, avoid_times={len(params.avoid_times)}, avoid_ranges={len(params.avoid_time_ranges)}")
        print("DEBUG: ---------------------------")
