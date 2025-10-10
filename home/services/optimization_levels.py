"""
시간표 생성 최적화 수준 설정
사용자가 선택할 수 있는 최적화 깊이를 정의
"""


class OptimizationLevel:
    """
    최적화 수준 설정 - 쉽게 수정 가능한 구조
    각 레벨의 solution 수를 조정하여 탐색 깊이 제어
    """

    BASIC = {
        'name': 'BASIC',
        'display_name': '기본 최적화',
        'solutions': 100,           # 생성할 시간표 수 (쉽게 수정 가능)
        'phase1_time': 10,          # Phase 1 최대 시간(초)
        'phase2_time': 30,          # Phase 2 최대 시간(초)
        'min_quality': 0.85,        # 최적값 대비 최소 품질 (85%)
        'num_workers': 4,           # 병렬 처리 워커 수
        'description': '빠른 결과 (약 30초)',
        'return_count': 20          # 최종 반환할 시간표 수
    }

    ADVANCED = {
        'name': 'ADVANCED',
        'display_name': '고급 최적화',
        'solutions': 500,           # 생성할 시간표 수 (쉽게 수정 가능)
        'phase1_time': 20,
        'phase2_time': 60,
        'min_quality': 0.90,        # 90% 이상 품질
        'num_workers': 8,
        'description': '균형잡힌 결과 (약 1분)',
        'return_count': 20
    }

    EXPERT = {
        'name': 'EXPERT',
        'display_name': '전문가 최적화',
        'solutions': 1000,          # 생성할 시간표 수 (쉽게 수정 가능)
        'phase1_time': 30,
        'phase2_time': 120,
        'min_quality': 0.92,        # 92% 이상 품질
        'num_workers': 8,
        'description': '고품질 결과 (약 2분)',
        'return_count': 30          # Expert는 더 많은 결과 반환
    }

    ULTRA = {
        'name': 'ULTRA',
        'display_name': '울트라 최적화',
        'solutions': 3000,          # 생성할 시간표 수 (쉽게 수정 가능)
        'phase1_time': 60,
        'phase2_time': 240,
        'min_quality': 0.95,        # 95% 이상 품질
        'num_workers': 12,
        'description': '최상의 결과 (약 4분)',
        'return_count': 30
    }

    # 커스텀 레벨 예시 (필요시 쉽게 추가 가능)
    CUSTOM = {
        'name': 'CUSTOM',
        'display_name': '사용자 정의',
        'solutions': 2000,          # 원하는 수로 조정
        'phase1_time': 45,
        'phase2_time': 180,
        'min_quality': 0.93,
        'num_workers': 10,
        'description': '사용자 정의 설정',
        'return_count': 25
    }

    @classmethod
    def get_level(cls, level_name='ADVANCED'):
        """
        레벨 이름으로 설정 가져오기

        Args:
            level_name: 최적화 레벨 이름 (BASIC, ADVANCED, EXPERT, ULTRA, CUSTOM)

        Returns:
            해당 레벨의 설정 딕셔너리
        """
        levels = {
            'BASIC': cls.BASIC,
            'ADVANCED': cls.ADVANCED,
            'EXPERT': cls.EXPERT,
            'ULTRA': cls.ULTRA,
            'CUSTOM': cls.CUSTOM
        }
        return levels.get(level_name.upper(), cls.ADVANCED)

    @classmethod
    def get_all_levels(cls):
        """
        모든 최적화 레벨 정보 반환 (UI 표시용)

        Returns:
            레벨 정보 리스트
        """
        return [
            {
                'value': 'BASIC',
                'name': cls.BASIC['display_name'],
                'description': cls.BASIC['description'],
                'solutions': cls.BASIC['solutions']
            },
            {
                'value': 'ADVANCED',
                'name': cls.ADVANCED['display_name'],
                'description': cls.ADVANCED['description'],
                'solutions': cls.ADVANCED['solutions']
            },
            {
                'value': 'EXPERT',
                'name': cls.EXPERT['display_name'],
                'description': cls.EXPERT['description'],
                'solutions': cls.EXPERT['solutions']
            },
            {
                'value': 'ULTRA',
                'name': cls.ULTRA['display_name'],
                'description': cls.ULTRA['description'],
                'solutions': cls.ULTRA['solutions']
            }
        ]

    @classmethod
    def estimate_time(cls, level_name):
        """
        예상 소요 시간 계산

        Args:
            level_name: 최적화 레벨 이름

        Returns:
            예상 소요 시간 (초)
        """
        level = cls.get_level(level_name)
        return level['phase1_time'] + level['phase2_time']