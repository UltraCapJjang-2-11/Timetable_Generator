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
from ..utils import get_effective_general_category, DummyObj


class ModelBuilder:
    """CP-SAT 모델 구성"""

    def __init__(self):
        self.building_service = BuildingDistanceService()

    def build_model(
        self,
        candidate_data: List[Dict[str, Any]],
        constraints: ConstraintData
    ) -> tuple[cp_model.CpModel, Dict[int, cp_model.IntVar]]:
        """
        CP-SAT 모델 구성

        Args:
            candidate_data: 후보 과목 데이터 리스트
            constraints: 제약 조건

        Returns:
            (모델, 변수 딕셔너리) 튜플
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

        # 6. 목적함수 설정
        self._set_objective_function(model, x, candidate_data, constraints)

        return model, x

    def _add_pre_added_constraints(
        self,
        model: cp_model.CpModel,
        x: Dict[int, cp_model.IntVar],
        candidate_data: List[Dict[str, Any]]
    ) -> None:
        """미리 추가된 과목 강제 포함"""
        for data in candidate_data:
            if data.get('pre_added', False):
                model.Add(x[data['id']] == 1)

    def _add_credit_constraints(
        self,
        model: cp_model.CpModel,
        x: Dict[int, cp_model.IntVar],
        candidate_data: List[Dict[str, Any]],
        constraints: ConstraintData
    ) -> None:
        """학점 제약 조건"""
        # 총 학점
        model.Add(
            sum(data['credit'] * x[data['id']] for data in candidate_data)
            == constraints.target_total
        )

        # 전공 학점
        model.Add(
            sum(data['credit'] * x[data['id']] for data in candidate_data
                if data['category'] in MAJOR_CATEGORIES)
            == constraints.target_major
        )

        # 교양 학점
        model.Add(
            sum(data['credit'] * x[data['id']] for data in candidate_data
                if get_effective_general_category(course=DummyObj({'effective': data.get('effective_category', None)}))
                or data['category'] not in MAJOR_CATEGORIES)
            == constraints.target_elective
        )

        # 교양 세부 카테고리별 상한 제약
        if constraints.missing_gen_sub:
            print("DEBUG: 교양 세부 카테고리별 제약 추가 중...")
            for category_name, shortage_credits in constraints.missing_gen_sub.items():
                category_courses = [
                    data for data in candidate_data
                    if data.get('effective_category') == category_name
                ]
                if category_courses:
                    model.Add(
                        sum(data['credit'] * x[data['id']] for data in category_courses)
                        <= shortage_credits
                    )
                    print(f"DEBUG: {category_name} 카테고리 - 최대 {shortage_credits}학점 제약 추가 (과목 {len(category_courses)}개)")

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
                times = [int(t) + CLASS_START_HOUR for t in sched['times'].split(',') if t.strip().isdigit()]
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
    ) -> None:
        """목적함수 설정"""
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

        # 6. 시간표 밀집도
        compactness_bonus = 0
        if constraints.prefer_compact:
            daily_classes = defaultdict(list)
            for data in candidate_data:
                for sch in data['schedule']:
                    day = sch['day']
                    times = [int(t) + CLASS_START_HOUR for t in sch['times'].split(',') if t.strip().isdigit()]
                    for t in times:
                        daily_classes[day].append((t, data['id']))

            # 밀집도 보너스 계산
            for day, time_list in daily_classes.items():
                if time_list:
                    times = sorted([t for t, _ in time_list])
                    if len(times) > 1:
                        gaps = sum(times[i+1] - times[i] - 1 for i in range(len(times)-1))
                        day_bonus = max(0, ScoringWeights.COMPACTNESS_BASE_BONUS - gaps * ScoringWeights.COMPACTNESS_GAP_PENALTY)
                        for _, course_id in time_list:
                            compactness_bonus += x[course_id] * day_bonus

            print(f"DEBUG: 밀집도 선호 활성화 - 공강 최소화 보너스 적용")

        # 최종 목적함수
        model.Maximize(
            graduation_priority * ScoringWeights.GRADUATION_PRIORITY_WEIGHT +
            preference_priority * ScoringWeights.PREFERENCE_WEIGHT +
            rating_priority * ScoringWeights.RATING_WEIGHT +
            compactness_bonus * ScoringWeights.COMPACTNESS_WEIGHT +
            required_priority * ScoringWeights.REQUIRED_COURSE_WEIGHT +
            elective_priority * ScoringWeights.ELECTIVE_COURSE_WEIGHT
        )
        print(f"DEBUG: 목적함수 가중치 - 졸업:{ScoringWeights.GRADUATION_PRIORITY_WEIGHT}, " +
              f"선호도:{ScoringWeights.PREFERENCE_WEIGHT}, " +
              f"평점:{ScoringWeights.RATING_WEIGHT}, " +
              f"밀집도:{ScoringWeights.COMPACTNESS_WEIGHT}, " +
              f"전필:{ScoringWeights.REQUIRED_COURSE_WEIGHT}, " +
              f"전선:{ScoringWeights.ELECTIVE_COURSE_WEIGHT}")


class SolutionFinder:
    """최적해 및 다양한 해 찾기"""

    def __init__(self):
        pass

    def find_optimal_solution(
        self,
        model: cp_model.CpModel,
        x: Dict[int, cp_model.IntVar],
        candidate_data: List[Dict[str, Any]]
    ) -> Optional[float]:
        """
        Phase 1: 최적해 찾기

        Args:
            model: CP-SAT 모델
            x: 변수 딕셔너리
            candidate_data: 후보 과목 데이터

        Returns:
            최적 목적함수 값. 해를 찾지 못하면 None
        """
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = SolverParameters.PHASE1_MAX_TIME
        solver.parameters.num_search_workers = SolverParameters.PHASE1_NUM_WORKERS
        solver.parameters.linearization_level = SolverParameters.PHASE1_LINEARIZATION_LEVEL

        print("DEBUG: Starting Phase 1 optimization...")
        print(f"DEBUG: 후보 과목 수: {len(candidate_data)}개")

        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None

        best_value = solver.ObjectiveValue()
        print("DEBUG: Phase 1 Best objective =", best_value)

        # 디버그: 목적함수 구성요소 출력
        self._print_objective_components(solver, x, candidate_data)

        return best_value

    def find_multiple_solutions(
        self,
        model: cp_model.CpModel,
        x: Dict[int, cp_model.IntVar],
        candidate_data: List[Dict[str, Any]],
        review_summaries: Dict[tuple, Any],
        max_solutions: int = SolverParameters.PHASE2_MAX_SOLUTIONS
    ) -> List[List[Dict[str, Any]]]:
        """
        Phase 2: 다양한 해 찾기

        Args:
            model: CP-SAT 모델
            x: 변수 딕셔너리
            candidate_data: 후보 과목 데이터
            review_summaries: 강의 평점 정보
            max_solutions: 최대 해 개수

        Returns:
            시간표 리스트 (각 시간표는 과목 딕셔너리 리스트)
        """
        timetables_data = []
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = SolverParameters.PHASE2_MAX_TIME
        solver.parameters.num_search_workers = SolverParameters.PHASE2_NUM_WORKERS

        print("DEBUG: Starting Phase 2 search for multiple solutions...")

        # 최대 max_solutions개의 서로 다른 시간표 찾기
        for i in range(max_solutions):
            status = solver.Solve(model)

            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                solution = []
                selected_ids = []

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

                timetables_data.append(solution)
                print(f"DEBUG: Found solution #{i+1} with {len(solution)} courses")

                # 다음 반복에서 같은 해를 찾지 않도록 제약 추가
                model.Add(sum(x[cid] for cid in selected_ids) < len(selected_ids))
            else:
                print(f"DEBUG: No more solutions found after {i} iterations")
                break

        print(f"DEBUG: Phase 2 search finished. Total solutions: {len(timetables_data)}")
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

        print(f"DEBUG: Phase 1 components - Graduation: {grad_val}, Preference: {pref_val}, Rating: {rating_val}, Required: {req_val}, Elective: {elec_val}")
