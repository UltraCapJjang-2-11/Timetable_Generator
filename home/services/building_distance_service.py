"""
건물 간 거리 및 이동 시간 관리 서비스
싱글톤 패턴을 사용하여 건물 거리 데이터를 효율적으로 캐싱
"""

import re
from typing import Optional, Dict, Tuple
from data_manager.models import BuildingDistance
from ..views.timetable_config import DEFAULT_WALKING_TIME


class BuildingDistanceService:
    """
    건물 간 거리 및 이동 시간 관리 서비스
    싱글톤 패턴 적용으로 전역 변수 제거 및 스레드 안전성 개선
    """

    _instance: Optional['BuildingDistanceService'] = None
    _distance_cache: Optional[Dict[Tuple[str, str], int]] = None

    def __new__(cls):
        """싱글톤 인스턴스 생성"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """초기화 (캐시가 없을 경우에만 로드)"""
        if self._distance_cache is None:
            self._load_cache()

    def _load_cache(self) -> None:
        """건물 거리 데이터를 DB에서 로드하여 메모리에 캐싱"""
        self._distance_cache = {}
        for dist in BuildingDistance.objects.all():
            key = (dist.from_building, dist.to_building)
            self._distance_cache[key] = dist.walking_time
        print(f"DEBUG: 건물 거리 캐시 로드 완료 - {len(self._distance_cache)}개 항목")

    def get_distance(self, from_building: str, to_building: str) -> int:
        """
        두 건물 간 이동 시간 조회

        Args:
            from_building: 출발 건물 코드 (예: "N14")
            to_building: 도착 건물 코드 (예: "S1")

        Returns:
            이동 시간 (분). 캐시에 없으면 기본값(5분) 반환
        """
        if not from_building or not to_building:
            return 0

        if from_building == to_building:
            return 0

        # 캐시에서 조회
        if self._distance_cache is None:
            self._load_cache()

        return self._distance_cache.get(
            (from_building, to_building),
            DEFAULT_WALKING_TIME
        )

    def reload_cache(self) -> None:
        """캐시 재로드 (DB 변경 시 호출)"""
        self._load_cache()

    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._distance_cache = None

    @staticmethod
    def extract_building_number(location: str) -> Optional[str]:
        """
        강의실 위치에서 건물 번호 추출

        Args:
            location: 강의실 위치 문자열 (예: "N14-1325")

        Returns:
            건물 번호 (예: "N14"). 추출 실패 시 None
        """
        if not location:
            return None

        # 정규 표현식으로 건물 번호 추출
        match = re.match(r'^([NSEW]\d+)', location.upper())
        if match:
            return match.group(1)
        return None


# 전역 인스턴스 (하위 호환성을 위해 유지)
_building_distance_service = BuildingDistanceService()


def get_building_distance(from_building: str, to_building: str) -> int:
    """
    두 건물 간 이동 시간 조회 (하위 호환성을 위한 함수)

    Args:
        from_building: 출발 건물
        to_building: 도착 건물

    Returns:
        이동 시간 (분)
    """
    return _building_distance_service.get_distance(from_building, to_building)


def extract_building_number(location: str) -> Optional[str]:
    """
    강의실 위치에서 건물 번호 추출 (하위 호환성을 위한 함수)

    Args:
        location: 강의실 위치

    Returns:
        건물 번호 또는 None
    """
    return BuildingDistanceService.extract_building_number(location)
