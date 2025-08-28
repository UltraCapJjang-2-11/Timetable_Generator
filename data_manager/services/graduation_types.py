from dataclasses import dataclass, asdict
import json
from typing import Iterable, List


@dataclass
class RuleResult:
    """
    단일 규칙에 대한 판별 결과를 저장하는 데이터 클래스
    - 직렬화 지원: to_dict()
    """
    rule_description: str
    category_name: str
    required_credits: int
    earned_credits: float
    is_satisfied: bool
    remark: str

    def to_dict(self) -> dict:
        """JSON 응답에 바로 사용 가능한 dict로 직렬화합니다."""
        return asdict(self)

    def to_json(self, ensure_ascii: bool = False) -> str:
        """해당 결과를 JSON 문자열로 직렬화합니다."""
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii)

    @staticmethod
    def list_to_dicts(results: Iterable["RuleResult"]) -> List[dict]:
        """RuleResult 리스트를 JSON 직렬화 가능한 dict 리스트로 변환합니다."""
        return [r.to_dict() for r in results]

    @staticmethod
    def list_to_json(results: Iterable["RuleResult"], ensure_ascii: bool = False) -> str:
        """RuleResult 리스트를 JSON 문자열로 직렬화합니다."""
        return json.dumps(RuleResult.list_to_dicts(results), ensure_ascii=ensure_ascii)


