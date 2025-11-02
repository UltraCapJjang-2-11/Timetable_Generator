"""
시간표 최적화 서비스 (CP-SAT 기반)
ModelBuilder: CP-SAT 모델 구성
SolutionFinder: 최적해 및 다양한 해 찾기
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from ortools.sat.python import cp_model

from ..views.timetable_types import ConstraintData
from ..views.timetable_config import (
    ScoringWeights,
    SolverParameters,
    MAX_WALKING_TIME_NO_LIMIT,
    CLASS_START_HOUR,
    MAJOR_CATEGORIES
)
from .building_distance_service import BuildingDistanceService
from .optimization_levels import OptimizationLevel
from ..utils import (
    get_effective_general_category,
    DummyObj,
    parse_time_slots,
    parse_time_slots_to_set
)


class ModelBuilder:
    """CP-SAT 모델 구성"""

    def __init__(self):
        self.building_service = BuildingDistanceService()

    def build_model(
        self,
        candidate_data: List[Dict[str, Any]],
        constraints: ConstraintData
    ) -> tuple[cp_model.CpModel, Dict[int, cp_model.IntVar], Any]:
        """
        CP-SAT 모델 구성

        Args:
            candidate_data: 후보 과목 데이터 리스트
            constraints: 제약 조건

        Returns:
            (모델, 변수 딕셔너리, 목적함수 표현식) 튜플
        """
        model = cp_model.CpModel()
        x = {}

        # 1. 변수 생성
        for data in candidate_data:
            x[data['id']] = model.NewBoolVar(f"course_{data['id']}")

        # 2. 미리 추가된 과목 강제 포함
        self._add_pre_added_constraints(model, x, candidate_data)

        # 3. 학점 제약 조건
        self._add_credit_constraints(model, x, candidate_data, constraints)

        # 4. 시간표 충돌 제약
        slot_mapping, name_groups = self._add_conflict_constraints(model, x, candidate_data)

        # 5. 건물 간 이동시간 제약
        self._add_distance_constraints(model, x, candidate_data, constraints)

        # 6. 목적함수 설정 및 표현식 저장
        objective_expr = self._set_objective_function(model, x, candidate_data, constraints)

        return model, x, objective_expr

    def _add_pre_added_constraints(
        self,
        model: cp_model.CpModel,
        x: Dict[int, cp_model.IntVar],
        candidate_data: List[Dict[str, Any]]
    ) -> None:
        """미리 추가된 과목 강제 포함 (검증 포함)"""
        pre_added_courses = [data for data in candidate_data if data.get('pre_added', False)]

        if pre_added_courses:
            # 1. 사전 추가 과목들의 시간 충돌 체크
            time_conflicts = []
            for i, course1 in enumerate(pre_added_courses):
                for j, course2 in enumerate(pre_added_courses[i+1:], i+1):
                    for sch1 in course1['schedule']:
                        for sch2 in course2['schedule']:
                            if sch1['day'] == sch2['day']:
                                times1 = parse_time_slots_to_set(sch1['times'])
                                times2 = parse_time_slots_to_set(sch2['times'])
                                if times1 & times2:  # 교집합이 있으면 충돌
                                    time_conflicts.append((course1['course_name'], course2['course_name']))

            if time_conflicts:
                conflict_msg = ", ".join([f"{c1} ↔ {c2}" for c1, c2 in time_conflicts])
                print(f"WARNING: 사전 추가 과목 간 시간 충돌 감지: {conflict_msg}")

            # 2. 사전 추가 과목들의 학점 합계 체크
            pre_added_credits = sum(data['credit'] for data in pre_added_courses)
            print(f"DEBUG: 사전 추가 과목 {len(pre_added_courses)}개, 총 {pre_added_credits}학점")

            # 3. 사전 추가 과목 강제 포함
            for data in pre_added_courses:
                model.Add(x[data['id']] == 1)

    def _add_credit_constraints(
        self,
        model: cp_model.CpModel,
        x: Dict[int, cp_model.IntVar],
        candidate_data: List[Dict[str, Any]],
        constraints: ConstraintData
    ) -> None:
        """학점 제약 조건"""
        # 미리 추가된 과목과 새로 추가할 과목 분리
        pre_added_courses = [data for data in candidate_data if data.get('pre_added', False)]
        new_courses = [data for data in candidate_data if not data.get('pre_added', False)]

        # 미리 추가된 과목의 학점 계산
        pre_added_total = sum(data['credit'] for data in pre_added_courses)

        pre_added_major = sum(
            data['credit'] for data in pre_added_courses
            if data['category'] in MAJOR_CATEGORIES
        )

        pre_added_elective = sum(
            data['credit'] for data in pre_added_courses
            if (data.get('effective_category') and data.get('effective_category') != '')
            or data['category'] not in MAJOR_CATEGORIES
        )

        # 남은 학점 계산
        remaining_total = constraints.target_total - pre_added_total
        remaining_major = constraints.target_major - pre_added_major
        remaining_elective = constraints.target_elective - pre_added_elective

        if pre_added_courses:
            print(f"DEBUG: 미리 추가된 과목 학점 - 총 {pre_added_total}학점 (전공 {pre_added_major}학점, 교양 {pre_added_elective}학점)")
            print(f"DEBUG: 남은 학점 - 총 {remaining_total}학점 (전공 {remaining_major}학점, 교양 {remaining_elective}학점)")

        # 총 학점 제약 (전체 과목 대상)
        model.Add(
            sum(data['credit'] * x[data['id']] for data in candidate_data)
            == constraints.target_total
        )

        # 전공 학점 제약 (새로 추가할 과목만 대상)
        if remaining_major > 0:
            model.Add(
                sum(data['credit'] * x[data['id']] for data in new_courses
                    if data['category'] in MAJOR_CATEGORIES)
                == remaining_major
            )
        elif remaining_major == 0:
            # 전공 학점을 이미 다 채웠으면 새로운 전공 과목을 추가하지 않음
            model.Add(
                sum(x[data['id']] for data in new_courses
                    if data['category'] in MAJOR_CATEGORIES)
                == 0
            )

        # 교양 학점 제약 (새로 추가할 과목만 대상)
        if remaining_elective > 0:
            model.Add(
                sum(data['credit'] * x[data['id']] for data in new_courses
                    if (data.get('effective_category') and data.get('effective_category') != '')
                    or data['category'] not in MAJOR_CATEGORIES)
                == remaining_elective
            )
        elif remaining_elective == 0:
            # 교양 학점을 이미 다 채웠으면 새로운 교양 과목을 추가하지 않음
            model.Add(
                sum(x[data['id']] for data in new_courses
                    if (data.get('effective_category') and data.get('effective_category') != '')
                    or data['category'] not in MAJOR_CATEGORIES)
                == 0
            )

        # 교양 세부 카테고리별 제약 (상한 및 하한 체크)
        if constraints.missing_gen_sub:
            print("DEBUG: 교양 세부 카테고리별 제약 추가 중...")
            for category_name, shortage_credits in constraints.missing_gen_sub.items():
                # 해당 카테고리의 모든 과목과 미리 추가된 과목 분리
                category_courses = [
                    data for data in candidate_data
                    if data.get('effective_category') == category_name
                ]

                category_pre_added = [
                    data for data in category_courses
                    if data.get('pre_added', False)
                ]

                category_new_courses = [
                    data for data in category_courses
                    if not data.get('pre_added', False)
                ]

                if category_courses:
                    # 미리 추가된 과목의 학점 계산
                    pre_added_category_credits = sum(data['credit'] for data in category_pre_added)

                    # 남은 부족 학점 계산
                    remaining_shortage = shortage_credits - pre_added_category_credits

                    if remaining_shortage > 0:
                        # 새로 추가할 과목의 학점 합계
                        new_category_credit_sum = sum(data['credit'] * x[data['id']] for data in category_new_courses)

                        # 상한 제약: 필요 이상 수강하지 않도록
                        model.Add(new_category_credit_sum <= remaining_shortage)

                        # 하한 제약: 가능한 범위 내에서 최대한 충족하도록
                        # 2학점 과목만 있는 경우를 고려하여 유연하게 처리
                        available_credits = sum(data['credit'] for data in category_new_courses)
                        min_achievable = min(remaining_shortage, available_credits)

                        # 최소한 달성 가능한 만큼은 채우도록 soft constraint 추가
                        # (hard constraint로 하면 해가 없을 수 있으므로 objective에 반영)
                        print(f"DEBUG: {category_name} 카테고리 - 목표 {shortage_credits}학점, 미리 추가 {pre_added_category_credits}학점, 남은 목표 {remaining_shortage}학점, 가능 {available_credits}학점, 과목 {len(category_new_courses)}개")
                    elif remaining_shortage == 0:
                        # 해당 카테고리는 이미 충족되었으므로 새로운 과목을 추가하지 않음
                        if category_new_courses:
                            model.Add(sum(x[data['id']] for data in category_new_courses) == 0)
                        print(f"DEBUG: {category_name} 카테고리 - 이미 충족됨 (미리 추가 {pre_added_category_credits}학점)")
                    else:
                        # 미리 추가된 학점이 목표보다 많은 경우 (초과)
                        print(f"DEBUG: {category_name} 카테고리 - 초과 (미리 추가 {pre_added_category_credits}학점 > 목표 {shortage_credits}학점)")

    def _add_conflict_constraints(
        self,
        model: cp_model.CpModel,
        x: Dict[int, cp_model.IntVar],
        candidate_data: List[Dict[str, Any]]
    ) -> tuple[Dict, Dict]:
        """시간표 충돌 제약"""
        # 시간 슬롯 매핑
        slot_mapping = defaultdict(list)
        for data in candidate_data:
            for sched in data['schedule']:
                day = sched['day']
                for t in sched['times'].split(","):
                    if t.strip().isdigit():
                        slot = int(t.strip()) + CLASS_START_HOUR
                        slot_mapping[(day, slot)].append(data['id'])

        # 동일 시간대에 최대 1개 과목
        for (day, slot), ids in slot_mapping.items():
            model.Add(sum(x[cid] for cid in ids) <= 1)

        # 동일 강의명 제약
        name_groups = defaultdict(list)
        for data in candidate_data:
            name_groups[data['course_name']].append(data['id'])
        for name, ids in name_groups.items():
            model.Add(sum(x[cid] for cid in ids) <= 1)

        return slot_mapping, name_groups

    def _add_distance_constraints(
        self,
        model: cp_model.CpModel,
        x: Dict[int, cp_model.IntVar],
        candidate_data: List[Dict[str, Any]],
        constraints: ConstraintData
    ) -> None:
        """건물 간 이동시간 제약"""
        if constraints.max_walking_time >= MAX_WALKING_TIME_NO_LIMIT:
            return  # "상관없음" 옵션

        # 시간-과목 매핑 구성
        time_course_map = defaultdict(lambda: defaultdict(list))
        for data in candidate_data:
            if not data.get('buildings'):
                continue
            for sched in data['schedule']:
                day = sched['day']
                times = parse_time_slots(sched['times'], add_base_hour=True)
                for t in times:
                    time_course_map[day][t].append(data)

        # 연속된 시간에 수업이 있는 경우 거리 체크
        checked_pairs = set()
        for day in time_course_map:
            for hour in sorted(time_course_map[day].keys()):
                if hour + 1 not in time_course_map[day]:
                    continue

                curr_courses = time_course_map[day][hour]
                next_courses = time_course_map[day][hour + 1]

                for curr in curr_courses:
                    for next_c in next_courses:
                        if curr['id'] >= next_c['id']:
                            continue

                        pair_key = (curr['id'], next_c['id'])
                        if pair_key in checked_pairs:
                            continue

                        # 두 과목의 건물 간 최대 거리 계산
                        max_distance = 0
                        for curr_bldg in curr.get('buildings', []):
                            for next_bldg in next_c.get('buildings', []):
                                distance = self.building_service.get_distance(curr_bldg, next_bldg)
                                max_distance = max(max_distance, distance)

                        if max_distance > constraints.max_walking_time:
                            model.Add(x[curr['id']] + x[next_c['id']] <= 1)
                            checked_pairs.add(pair_key)

    def _set_objective_function(
        self,
        model: cp_model.CpModel,
        x: Dict[int, cp_model.IntVar],
        candidate_data: List[Dict[str, Any]],
        constraints: ConstraintData
    ) -> Any:
        """목적함수 설정 및 목적함수 표현식 반환"""
        # 1. 졸업요건 충족도
        graduation_priority = sum(
            x[data['id']] * data.get('graduation_priority', 0)
            for data in candidate_data
        )

        # 2. 사용자 선호도 점수
        preference_priority = sum(
            x[data['id']] * data.get('preference_score', 0)
            for data in candidate_data
        )

        # 3. 강의 평점 점수
        rating_priority = sum(
            x[data['id']] * data.get('rating_score', 0)
            for data in candidate_data
        )

        # 4. 전공필수 우선
        required_priority = sum(
            x[data['id']] for data in candidate_data
            if data['category'] == '전공필수' and (
                data['year'] == "전학년" or (
                    data['year'] and data['year'][0].isdigit() and int(data['year'][0]) <= 100
                )
            )
        )

        # 5. 동일학년 전공선택 우선
        elective_priority = sum(
            x[data['id']] for data in candidate_data
            if data['category'] == '전공선택' and data.get('is_same_year', False)
        )

        # 6. 교양 카테고리 충족도 보너스
        gen_category_bonus = 0
        if constraints.missing_gen_sub:
            for category_name, shortage_credits in constraints.missing_gen_sub.items():
                category_courses = [
                    data for data in candidate_data
                    if data.get('effective_category') == category_name
                ]
                if category_courses:
                    # 해당 카테고리 과목들에 추가 보너스 부여
                    for data in category_courses:
                        # 부족 학점 대비 과목 학점 비율에 따른 보너스
                        bonus = min(100, (data['credit'] / max(1, shortage_credits)) * 100)
                        gen_category_bonus += x[data['id']] * int(bonus)

        # 7. 시간표 밀집도 (개선된 로직)
        compactness_bonus = 0
        if constraints.prefer_compact:
            print(f"DEBUG: 밀집도 선호 활성화됨 (prefer_compact=True)")
            print(f"DEBUG:   - 공강시간 패널티: {ScoringWeights.COMPACTNESS_GAP_PENALTY}점/시간")
            print(f"DEBUG:   - 연속 수업 보너스: {ScoringWeights.COMPACTNESS_BASE_BONUS}점")

            # 각 요일별로 선택된 과목들의 시간 간격을 최소화
            for day in ['월', '화', '수', '목', '금']:
                day_courses = []
                for data in candidate_data:
                    for sch in data['schedule']:
                        if sch['day'] == day:
                            times = parse_time_slots(sch['times'], add_base_hour=True)
                            if times:
                                day_courses.append((min(times), max(times), data['id'], data['course_name']))

                if len(day_courses) >= 2:
                    # 시간순으로 정렬
                    day_courses.sort(key=lambda x: x[0])
                    print(f"DEBUG:   {day}요일 - {len(day_courses)}개 과목:")
                    for start, end, cid, name in day_courses:
                        print(f"DEBUG:     - {name}: {start}교시~{end}교시")

                    # 연속된 과목들 간의 공강 계산 (개선)
                    for i in range(len(day_courses) - 1):
                        start1, end1, id1, name1 = day_courses[i]
                        start2, end2, id2, name2 = day_courses[i + 1]

                        gap = start2 - end1 - 1  # 공강 시간

                        if gap > 0:
                            # 공강이 있는 경우 페널티
                            penalty = gap * ScoringWeights.COMPACTNESS_GAP_PENALTY * 2  # 페널티 강화
                            both_selected = model.NewBoolVar(f'gap_{day}_{i}')
                            model.AddMultiplicationEquality(both_selected, [x[id1], x[id2]])
                            compactness_bonus += both_selected * (-penalty)
                            print(f"DEBUG:     공강 {gap}시간 발생: {name1} → {name2} (패널티 {penalty}점)")
                        elif gap == 0:
                            # 연속된 수업인 경우 보너스
                            consecutive_bonus = ScoringWeights.COMPACTNESS_BASE_BONUS
                            both_selected = model.NewBoolVar(f'consecutive_{day}_{i}')
                            model.AddMultiplicationEquality(both_selected, [x[id1], x[id2]])
                            compactness_bonus += both_selected * consecutive_bonus
                            print(f"DEBUG:     연속 수업: {name1} → {name2} (보너스 {consecutive_bonus}점)")

                    # 하루 전체 시간 범위에 대한 패널티 (첫 수업부터 마지막 수업까지)
                    if len(day_courses) > 0:
                        first_start = day_courses[0][0]
                        last_end = day_courses[-1][1]
                        total_span = last_end - first_start + 1
                        total_class_time = sum(end - start + 1 for start, end, _, _ in day_courses)
                        total_gap = total_span - total_class_time

                        if total_gap > 0:
                            # 전체 공강 시간에 대한 추가 패널티
                            span_penalty_var = model.NewIntVar(0, 1000, f'span_penalty_{day}')
                            day_active = model.NewBoolVar(f'day_active_{day}')

                            # 해당 요일에 수업이 있는지 확인
                            model.Add(sum(x[cid] for _, _, cid, _ in day_courses) >= 1).OnlyEnforceIf(day_active)
                            model.Add(sum(x[cid] for _, _, cid, _ in day_courses) == 0).OnlyEnforceIf(day_active.Not())

                            # 요일이 활성화되면 패널티 적용 (강화)
                            model.Add(span_penalty_var == total_gap * 50).OnlyEnforceIf(day_active)  # 20 -> 50
                            model.Add(span_penalty_var == 0).OnlyEnforceIf(day_active.Not())
                            compactness_bonus = compactness_bonus - span_penalty_var

                            print(f"DEBUG:   {day}요일 전체 범위: {first_start}~{last_end}교시 (총 공강 {total_gap}시간)")

            print(f"DEBUG: 밀집도 보너스/페널티 적용 완료 (가중치: {ScoringWeights.COMPACTNESS_WEIGHT})")

        # 최종 목적함수 표현식 생성
        objective_expr = (
            graduation_priority * ScoringWeights.GRADUATION_PRIORITY_WEIGHT +
            preference_priority * ScoringWeights.PREFERENCE_WEIGHT +
            rating_priority * ScoringWeights.RATING_WEIGHT +
            compactness_bonus * ScoringWeights.COMPACTNESS_WEIGHT +
            required_priority * ScoringWeights.REQUIRED_COURSE_WEIGHT +
            elective_priority * ScoringWeights.ELECTIVE_COURSE_WEIGHT +
            gen_category_bonus * ScoringWeights.GENERAL_CATEGORY_BONUS_WEIGHT
        )

        # 목적함수 설정
        model.Maximize(objective_expr)

        print(f"DEBUG: 목적함수 가중치 - 졸업:{ScoringWeights.GRADUATION_PRIORITY_WEIGHT}, " +
              f"선호도:{ScoringWeights.PREFERENCE_WEIGHT}, " +
              f"평점:{ScoringWeights.RATING_WEIGHT}, " +
              f"밀집도:{ScoringWeights.COMPACTNESS_WEIGHT if constraints.prefer_compact else 0}, " +
              f"전필:{ScoringWeights.REQUIRED_COURSE_WEIGHT}, " +
              f"전선:{ScoringWeights.ELECTIVE_COURSE_WEIGHT}")

        # 목적함수 표현식 반환
        return objective_expr


class SolutionFinder:
    """최적해 및 다양한 해 찾기"""

    def __init__(self):
        pass

    def find_optimal_solution(
        self,
        model: cp_model.CpModel,
        x: Dict[int, cp_model.IntVar],
        candidate_data: List[Dict[str, Any]],
        optimization_level: str = 'ADVANCED'
    ) -> Optional[float]:
        """
        Phase 1: 최적해 찾기

        Args:
            model: CP-SAT 모델
            x: 변수 딕셔너리
            candidate_data: 후보 과목 데이터
            optimization_level: 최적화 수준 (BASIC, ADVANCED, EXPERT, ULTRA)

        Returns:
            최적 목적함수 값. 해를 찾지 못하면 None
        """
        # 최적화 레벨 설정 로드
        level_config = OptimizationLevel.get_level(optimization_level)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = level_config['phase1_time']
        solver.parameters.num_search_workers = level_config['num_workers']
        solver.parameters.linearization_level = SolverParameters.PHASE1_LINEARIZATION_LEVEL

        print("\n" + "="*80)
        print("🔍 Phase 1: 최적해 탐색 시작")
        print("="*80)
        print(f"🎯 최적화 수준: {level_config['display_name']}")
        print(f"후보 과목 수: {len(candidate_data)}개")
        print(f"최대 시간: {level_config['phase1_time']}초")
        print(f"병렬 워커: {level_config['num_workers']}개")

        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print("❌ Phase 1: 해를 찾을 수 없음")
            return None

        best_value = solver.ObjectiveValue()

        # Phase 1 결과 상세 출력
        print("\n✅ Phase 1 완료")
        print(f"최적 목적함수 값: {best_value:,.0f}")
        print("\n📊 목적함수 구성요소 분석:")

        # 디버그: 목적함수 구성요소 출력
        self._print_objective_components(solver, x, candidate_data)

        # 선택된 과목 출력
        selected_courses = []
        for data in candidate_data:
            if solver.Value(x[data['id']]) == 1:
                selected_courses.append(data['course_name'])

        print(f"\n선택된 과목 ({len(selected_courses)}개): {', '.join(selected_courses)}")
        print("="*80 + "\n")

        return best_value

    def find_multiple_solutions(
        self,
        model: cp_model.CpModel,
        x: Dict[int, cp_model.IntVar],
        candidate_data: List[Dict[str, Any]],
        review_summaries: Dict[tuple, Any],
        optimization_level: str = 'ADVANCED',
        optimal_value: Optional[float] = None,
        objective_expr: Any = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Phase 2: 다양한 해 찾기 (개선된 버전)

        Args:
            model: CP-SAT 모델
            x: 변수 딕셔너리
            candidate_data: 후보 과목 데이터
            review_summaries: 강의 평점 정보
            optimization_level: 최적화 수준 (BASIC, ADVANCED, EXPERT, ULTRA)
            optimal_value: Phase 1에서 찾은 최적값
            objective_expr: 목적함수 표현식

        Returns:
            시간표 리스트 (각 시간표는 과목 딕셔너리 리스트)
        """
        # 최적화 레벨 설정 로드
        level_config = OptimizationLevel.get_level(optimization_level)
        max_solutions = level_config['solutions']

        timetables_data = []
        timetable_scores = []  # 각 시간표의 점수 추적
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = level_config['phase2_time']
        solver.parameters.num_search_workers = level_config['num_workers']

        print("\n" + "="*80)
        print("🔍 Phase 2: 다양한 시간표 생성 시작")
        print("="*80)
        print(f"🎯 최적화 수준: {level_config['display_name']}")
        print(f"목표: 최대 {max_solutions}개 시간표 생성")
        print(f"최대 시간: {level_config['phase2_time']}초")
        print(f"병렬 워커: {level_config['num_workers']}개")

        # Phase 1의 최적값을 활용하여 일정 범위 내의 해만 탐색
        if optimal_value is not None and objective_expr is not None:
            # 최적화 레벨에 따른 최소 품질 기준 적용
            min_quality = level_config['min_quality']
            min_acceptable_value = optimal_value * min_quality
            model.Add(objective_expr >= int(min_acceptable_value))
            print(f"최소 목적함수 값 제약: {min_acceptable_value:,.0f} (최적값의 {min_quality*100:.0f}%)")
            print(f"최적값: {optimal_value:,.0f}")

        print("\n시간표 생성 진행상황:")
        print("-" * 80)

        # 최대 max_solutions개의 서로 다른 시간표 찾기
        for i in range(max_solutions):
            status = solver.Solve(model)

            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                solution = []
                selected_ids = []
                current_objective_value = solver.ObjectiveValue()

                for data in candidate_data:
                    if solver.Value(x[data['id']]) == 1:
                        selected_ids.append(data['id'])

                        # 평점 정보 조회
                        avg_rating = None
                        review_key = (data.get('course_name', ''), data.get('instructor_name', ''))
                        if review_key in review_summaries and review_key[0] and review_key[1]:
                            avg_rating = float(review_summaries[review_key].avg_rating)

                        solution.append({
                            'course_id': data['id'],
                            'course_name': data.get('course_name', ''),
                            'course_code': data.get('course_code', ''),
                            'section': data.get('section', ''),
                            'credits': data.get('credit', 0),
                            'target_year': data.get('year', ''),
                            'instructor_name': data.get('instructor_name', ''),
                            'capacity': data.get('capacity', 0),
                            'dept_name': data.get('dept_name', ''),
                            'category_name': data.get('category', ''),
                            'semester': data.get('semester', ''),
                            'schedules': data.get('schedule', []),
                            'location': data.get('location', ''),
                            'avg_rating': avg_rating
                        })

                # percentage 계산을 먼저 수행
                percentage = (current_objective_value / optimal_value * 100) if optimal_value else 100
                course_names = [c['course_name'] for c in solution]

                # 시간표에 목적함수 값 추가
                solution_with_score = {
                    'courses': solution,
                    'objective_value': current_objective_value,
                    'objective_percentage': percentage
                }
                timetables_data.append(solution_with_score)

                # 시간표 점수 정보 저장
                timetable_scores.append({
                    'number': i + 1,
                    'objective_value': current_objective_value,
                    'percentage': percentage,
                    'num_courses': len(solution),
                    'courses': course_names
                })

                print(f"시간표 #{i+1:3d}: 목적함수값 {current_objective_value:8,.0f} ({percentage:5.1f}%) | {len(solution)}과목 | {', '.join(course_names[:3])}{'...' if len(course_names) > 3 else ''}")

                # 다음 반복에서 다양한 해를 찾도록 제약 추가
                # 개선된 다양성 전략: pre_added 과목을 제외한 과목들 중에서 최소 1개는 다르게
                pre_added_ids = [cid for cid in selected_ids
                                if any(data['id'] == cid and data.get('pre_added', False) for data in candidate_data)]
                non_pre_added_ids = [cid for cid in selected_ids if cid not in pre_added_ids]

                if non_pre_added_ids:
                    # 필수 과목이 아닌 과목들 중 최소 1개는 다르게 선택
                    # 이렇게 하면 필수 과목은 그대로 유지하면서도 다양한 조합 생성 가능
                    if len(non_pre_added_ids) > 2:
                        # 선택 가능한 과목이 3개 이상이면 최소 1개는 다르게
                        model.Add(sum(x[cid] for cid in non_pre_added_ids) <= len(non_pre_added_ids) - 1)
                    else:
                        # 선택 가능한 과목이 적으면 정확히 같은 조합만 제외
                        model.Add(sum(x[cid] for cid in selected_ids) < len(selected_ids))
                else:
                    # 모든 과목이 필수인 경우 (드문 경우)
                    model.Add(sum(x[cid] for cid in selected_ids) < len(selected_ids))
            else:
                print(f"\n⚠️ {i}개 시간표 생성 후 더 이상 해를 찾을 수 없음")
                break

        print("-" * 80)

        # Phase 2 결과 요약
        if timetable_scores:
            print(f"\n✅ Phase 2 완료: 총 {len(timetables_data)}개 시간표 생성")
            print("\n📊 목적함수 값 분포:")
            obj_values = [ts['objective_value'] for ts in timetable_scores]
            print(f"  - 최고점: {max(obj_values):,.0f}")
            print(f"  - 최저점: {min(obj_values):,.0f}")
            print(f"  - 평균: {sum(obj_values)/len(obj_values):,.0f}")
            print(f"  - 최적값 대비: {min(ts['percentage'] for ts in timetable_scores):.1f}% ~ {max(ts['percentage'] for ts in timetable_scores):.1f}%")

        print("="*80 + "\n")

        return timetables_data

    def _print_objective_components(
        self,
        solver: cp_model.CpSolver,
        x: Dict[int, cp_model.IntVar],
        candidate_data: List[Dict[str, Any]]
    ) -> None:
        """목적함수 구성요소 디버그 출력"""
        grad_val = sum(solver.Value(x[data['id']]) * data.get('graduation_priority', 0) for data in candidate_data)
        pref_val = sum(solver.Value(x[data['id']]) * data.get('preference_score', 0) for data in candidate_data)
        rating_val = sum(solver.Value(x[data['id']]) * data.get('rating_score', 0) for data in candidate_data)
        req_val = sum(solver.Value(x[data['id']]) for data in candidate_data
                     if data['category'] == '전공필수')
        elec_val = sum(solver.Value(x[data['id']]) for data in candidate_data
                      if data['category'] == '전공선택' and data.get('is_same_year', False))

        # 가중치 적용된 값 계산
        weighted_grad = grad_val * ScoringWeights.GRADUATION_PRIORITY_WEIGHT
        weighted_pref = pref_val * ScoringWeights.PREFERENCE_WEIGHT
        weighted_rating = rating_val * ScoringWeights.RATING_WEIGHT
        weighted_req = req_val * ScoringWeights.REQUIRED_COURSE_WEIGHT
        weighted_elec = elec_val * ScoringWeights.ELECTIVE_COURSE_WEIGHT

        print(f"  졸업요건: {grad_val:6.0f} × {ScoringWeights.GRADUATION_PRIORITY_WEIGHT:4} = {weighted_grad:10,.0f}")
        print(f"  선호도:   {pref_val:6.0f} × {ScoringWeights.PREFERENCE_WEIGHT:4} = {weighted_pref:10,.0f}")
        print(f"  평점:     {rating_val:6.0f} × {ScoringWeights.RATING_WEIGHT:4} = {weighted_rating:10,.0f}")
        print(f"  전공필수: {req_val:6.0f} × {ScoringWeights.REQUIRED_COURSE_WEIGHT:4} = {weighted_req:10,.0f}")
        print(f"  전공선택: {elec_val:6.0f} × {ScoringWeights.ELECTIVE_COURSE_WEIGHT:4} = {weighted_elec:10,.0f}")
        print(f"  ---")
        print(f"  총합: {weighted_grad + weighted_pref + weighted_rating + weighted_req + weighted_elec:10,.0f}")
