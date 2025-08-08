"""
시간표 생성 및 관리 관련 뷰
시간표 생성 알고리즘, 저장, 삭제 등의 시간표 관리 기능을 담당.
"""

import os
import json
import traceback
from collections import defaultdict
from django.db.models.functions import Upper
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from ortools.sat.python import cp_model

from data_manager.course.course_filter_service import CourseFilterService
from data_manager.models import *
from ..utils import (
    get_effective_general_category, get_simplified_category_name,
    extract_missing_required_major_courses, apply_time_constraints, DummyObj
)


def timetable_view(request):
    """
    시간표 생성 메인 페이지
    각 카테고리별 강의 목록을 조회하여 프론트엔드에 전달
    """
    service = CourseFilterService()

    # 25년도 2학기
    year = 2025
    term = "2학기"

    # 각 카테고리별 강의 조회
    major_required = service.course_search(year=year, term=term, category_name='전공필수').order_by('course_name')
    major_elective = service.course_search(year=year, term=term, category_name='전공선택').order_by('course_name')
    general_elective = service.course_search(year=year, term=term, category_name='교양').order_by('course_name')
    free_elective = service.course_search(year=year, term=term, category_name='일선').order_by('course_name')
    teaching_required = service.course_search(year=year, term=term, category_name='교직').order_by('course_name')

    return render(request, "home/timetable/timetable.html", {
        'major_required': major_required,
        'major_elective': major_elective,
        'general_elective': general_elective,
        'free_elective': free_elective,
        'teaching_required': teaching_required,
    })


def generate_timetable_stream(request):
    """
    시간표 생성 메인 함수
    사용자 제약조건을 기반으로 최적의 시간표 조합을 생성
    CP-SAT 알고리즘을 사용하여 최적화 문제를 해결
    """
    year = 2025
    term = '1학기'
    
    try:
        print("DEBUG: --- Timetable Generation Start ---")

        # 0) 자연어 파싱으로 받아온 필수 과목명 → Course ID 리스트(req_ids)
        req_names = request.GET.getlist('required_courses[]')
        req_ids = []
        
        svc = CourseFilterService()
        # 미리 연도·학기·카테고리를 넣어서 기본 queryset을 받아옵니다.
        major_qs = (
            svc.course_search(year=year, term=term, category_name='교양') |
            svc.course_search(year=year, term=term, category_name='전공')
        )
        for name in req_names:
            course = major_qs.filter(course_name__icontains=name).first()
            if course:
                req_ids.append(course.course_id)
        print("DEBUG: parsed required course IDs =", req_ids)

        # 1) GET 파라미터 파싱 (공강, 기존 추가 과목, 학점 등)
        free_days = request.GET.getlist('free_days[]')
        existing_ids = request.GET.getlist('existing_courses[]')
        exclude_names = request.GET.getlist('exclude_courses[]')
        print("DEBUG: exclude_courses =", exclude_names)
        
        try:
            pre_added_ids = [int(cid) for cid in existing_ids]
        except ValueError:
            pre_added_ids = []

        pre_added_ids = list(set(pre_added_ids + req_ids))
        print("DEBUG: final pre_added_ids (기존+필수과목) =", pre_added_ids)

        # 목표 학점 설정
        try:
            target_total = int(request.GET.get('total_credits', 18))
            target_major = int(request.GET.get('major_credits', 9))
            target_elective = int(request.GET.get('elective_credits', 9))
            
            # 전공 + 교양 학점이 총 학점을 초과하지 않도록 조정
            if target_major + target_elective > target_total:
                # 비율에 따라 조정
                ratio = target_total / (target_major + target_elective)
                target_major = int(target_major * ratio)
                target_elective = target_total - target_major
                print(f"DEBUG: 학점 조정됨 (초과) - 전공: {target_major}, 교양: {target_elective}")
            
            # 실제 목표 학점을 전공 + 교양 학점의 합으로 설정
            actual_total = target_major + target_elective
            if actual_total != target_total:
                print(f"DEBUG: 실제 목표 학점 조정 - 요청: {target_total}, 실제: {actual_total}")
                target_total = actual_total
            
            print("DEBUG: 최종 학점 설정 - total:", target_total, "major:", target_major, "elective:", target_elective)
        except ValueError:
            return JsonResponse({"error": "학점 파라미터가 올바르지 않습니다."}, status=500)

        print("DEBUG: free_days =", free_days)
        
        # 2) 신규: 시간 제약조건 파싱
        only_ranges = [json.loads(s) for s in request.GET.getlist('only_time_ranges[]')]
        avoid_times = [json.loads(s) for s in request.GET.getlist('avoid_times[]')]
        avoid_ranges = [json.loads(s) for s in request.GET.getlist('avoid_time_ranges[]')]
        
        # 특정 시간대 공강 파라미터 추가
        specific_avoid_times = [json.loads(s) for s in request.GET.getlist('specific_avoid_times[]')]
        specific_avoid_time_ranges = [json.loads(s) for s in request.GET.getlist('specific_avoid_time_ranges[]')]
        
        print("DEBUG: only_time_ranges =", only_ranges)
        print("DEBUG: avoid_times =", avoid_times)
        print("DEBUG: avoid_time_ranges =", avoid_ranges)
        print("DEBUG: specific_avoid_times =", specific_avoid_times)
        print("DEBUG: specific_avoid_time_ranges =", specific_avoid_time_ranges)

        # 3) 미리 추가된 과목 처리
        pre_added_courses = list(Courses.objects.filter(course_id__in=pre_added_ids))
        print("DEBUG: pre_added_courses count =", len(pre_added_courses))
        
        # 공강 요일에 대한 미리 추가된 과목 필터링
        if free_days:
            filtered = []
            for course in pre_added_courses:
                if not any(sch.day in free_days for sch in course.courseschedule_set.all()):
                    filtered.append(course)
            dropped = set(pre_added_ids) - set(c.course_id for c in filtered)
            if dropped:
                print("DEBUG: dropped pre_added courses on free_days:", dropped)
            pre_added_courses = filtered
            pre_added_ids = [c.course_id for c in pre_added_courses]

        # 3-3. 학생 정보 및 졸업 기록 로드
        student_id = request.user.id if request.user.is_authenticated else 1
        grad_record = GraduationRecord.objects.filter(user_id=student_id).last()
        
        try:
            if grad_record and grad_record.user_year:
                if grad_record.user_year == "전학년":
                    current_year = 100
                else:
                    current_year = int(grad_record.user_year[0])
            else:
                current_year = 3
        except Exception:
            current_year = 3
        print("DEBUG: current_year =", current_year)

        dept_name = grad_record.user_major if grad_record and grad_record.user_major else ""
        dept_obj = Department.objects.filter(dept_name=dept_name).first()
        student_dept_id = dept_obj.dept_id if dept_obj else None
        print("DEBUG: student_dept_id =", student_dept_id)

        # 완료한 과목 목록 처리
        completed_courses = []
        if grad_record and grad_record.completed_courses:
            try:
                completed_courses = json.loads(grad_record.completed_courses)
                completed_courses = [name.strip().upper() for name in completed_courses if name]
            except Exception as e:
                print("DEBUG: completed_courses parse error:", e)
                completed_courses = []
        print("DEBUG: completed_courses =", completed_courses)

        # 교양 세부 이수 상태 처리
        missing_gen_sub = {}
        try:
            missing_gen_sub = json.loads(grad_record.missing_general_sub or '{}')
            missing_gen_sub = {k: int(v) for k, v in missing_gen_sub.items()}
        except Exception as e:
            print("DEBUG: missing_general_sub parse error:", e)
            missing_gen_sub = {}
        print("DEBUG: missing_gen_sub =", missing_gen_sub)

        # 후보 강좌 조회 및 필터링
        candidate_qs = (
            (svc.course_search(year=year, term=term, category_name='전공') |
             svc.course_search(year=year, term=term, category_name='교양'))
            .annotate(upper_course_name=Upper('course_name'))
            .exclude(upper_course_name__in=[name.upper() for name in completed_courses])
        )

        candidates = []
        for course in candidate_qs:
            # 제외할 과목 필터
            if exclude_names:
                should_exclude = False
                course_id_str = str(course.course_id)
                for exclude_item in exclude_names:
                    exclude_item_str = str(exclude_item).strip()
                    # 과목 코드로 정확히 매칭
                    if course_id_str == exclude_item_str:
                        should_exclude = True
                        print(f"DEBUG: 과목 제외됨 (ID 매칭) - '{course.course_name}' (ID: {course.course_id})")
                        break
                    # 과목명으로도 매칭
                    elif not exclude_item_str.isdigit():
                        course_name_lower = course.course_name.lower().strip()
                        exclude_name_lower = exclude_item_str.lower().strip()
                        if (course_name_lower == exclude_name_lower or 
                            exclude_name_lower in course_name_lower or 
                            course_name_lower in exclude_name_lower):
                            should_exclude = True
                            print(f"DEBUG: 과목 제외됨 (이름 매칭) - '{course.course_name}'")
                            break
                if should_exclude:
                    continue
            
            # 전공 과목 필터
            if course.category.category_name in ["전공필수", "전공선택"]:
                if course.target_year != "전학년":
                    try:
                        course_year = int(course.target_year[0])
                    except Exception:
                        course_year = 0
                    if course_year > current_year:
                        continue

                # 소프트웨어학과/학부 예외 처리
                if student_dept_id == 48:  # 소프트웨어학과
                    student_dept_id = 50  # 소프트웨어학부

                if student_dept_id and course.dept_id and course.dept_id != student_dept_id:
                    continue

            # 기본 필터
            if course.course_id in pre_added_ids:
                continue
            if course.credits <= 0:
                continue
            # 시간표 '00' slot 제거
            if any(sch.times.strip() == "00" for sch in course.courseschedule_set.all()):
                continue
            # Free-day 충돌
            if any(sch.day in free_days for sch in course.courseschedule_set.all()):
                continue
            # 교양은 target_year가 전학년이어야
            if get_effective_general_category(course) and course.target_year != "전학년":
                continue
            if any("가상강의실" in (sch.location or "") for sch in course.courseschedule_set.all()):
                continue
            # 교양 강좌 세부 항목 확인
            if get_effective_general_category(course):
                effective_cat = get_effective_general_category(course)
                if missing_gen_sub.get(effective_cat, 0) == 0:
                    continue

            candidates.append(course)

        all_candidates = pre_added_courses + candidates
        print("DEBUG: candidates count =", len(candidates))
        print("DEBUG: all_candidates count =", len(all_candidates))

        # 각 후보 강좌의 스케줄 정보를 candidate_data에 저장
        candidate_data = []
        for course in all_candidates:
            schedule_list = []
            locations = []
            for sch in course.courseschedule_set.all():
                raw = sch.times.strip()
                if "@" in raw:
                    parts = raw.split("@", 1)
                    raw_time = parts[0].strip()
                    loc = parts[1].strip()
                else:
                    raw_time = raw
                    loc = sch.location
                if not raw_time:
                    continue
                schedule_list.append({
                    'day': sch.day,
                    'times': raw_time,
                    'location': loc
                })
                locations.append(loc)
            if not schedule_list:
                continue
            
            data_item = {
                'id': course.course_id,
                'course_name': course.course_name,
                'course_code': course.course_code,
                'section': course.section,
                'credit': course.credits,
                'credits': course.credits,
                'year': course.target_year,
                'instructor_name': course.instructor_name,
                'capacity': course.capacity,
                'dept_name': course.dept.dept_name if course.dept else '',
                'category': get_simplified_category_name(course),
                'semester': "2025 2학기",
                'schedule': schedule_list,
                'location': locations[0] if locations else "",
                'pre_added': course.course_id in pre_added_ids
            }
            # 교양 강좌: effective_category 추가
            if get_effective_general_category(course):
                data_item['effective_category'] = get_effective_general_category(course)
            candidate_data.append(data_item)
        
        print("DEBUG: candidate_data count =", len(candidate_data))

        # 시간 제약 조건 적용
        def in_range(h, start, end=None):
            return h >= start and (end is None or h < end)

        # only_time_ranges: 허용 범위 외 제거
        if only_ranges:
            filtered = []
            for d in candidate_data:
                ok = True
                for sched in d['schedule']:
                    hours = [int(t)+8 for t in sched['times'].split(',') if t.strip().isdigit()]
                    if not any(
                        sched['day'] in r['days']
                        and all(in_range(h, r['start_hour'], r.get('end_hour')) for h in hours)
                        for r in only_ranges
                    ):
                        ok = False
                        break
                if ok:
                    filtered.append(d)
            candidate_data = filtered
            print("DEBUG: only_time_ranges 적용 후 count =", len(candidate_data))

        # avoid_times / avoid_time_ranges: 회피 조건 제거
        if avoid_times or avoid_ranges:
            filtered = []
            for d in candidate_data:
                bad = False
                for sched in d['schedule']:
                    hours = [int(t)+8 for t in sched['times'].split(',') if t.strip().isdigit()]
                    if any(obj['day']==sched['day'] and h==obj['hour'] for obj in avoid_times for h in hours):
                        bad = True
                        break
                    if any(
                        sched['day'] in r['days']
                        and any(in_range(h, r['start_hour'], r.get('end_hour')) for h in hours)
                        for r in avoid_ranges
                    ):
                        bad = True
                        break
                if not bad:
                    filtered.append(d)
            candidate_data = filtered
            print("DEBUG: avoid_times/avoid_time_ranges 적용 후 count =", len(candidate_data))

        # specific_avoid_times / specific_avoid_time_ranges: 특정 요일+시간 회피
        if specific_avoid_times or specific_avoid_time_ranges:
            filtered = []
            for d in candidate_data:
                bad = False
                for sched in d['schedule']:
                    hours = [int(t)+8 for t in sched['times'].split(',') if t.strip().isdigit()]
                    
                    # 특정 요일+시간 회피
                    if any(obj['day']==sched['day'] and h==obj['hour'] 
                           for obj in specific_avoid_times for h in hours):
                        bad = True
                        break
                    
                    # 특정 요일+시간범위 회피
                    if any(
                        obj['day']==sched['day']
                        and any(h >= obj['start_hour'] and h < obj['end_hour'] for h in hours)
                        for obj in specific_avoid_time_ranges
                    ):
                        bad = True
                        break
                if not bad:
                    filtered.append(d)
            candidate_data = filtered
            print("DEBUG: specific_avoid_times/specific_avoid_time_ranges 적용 후 count =", len(candidate_data))

        # 동일학년 전공선택 강좌 우선 필터링
        for data in candidate_data:
            if data['category'] == '전공선택':
                if data['year'] == "전학년" or (
                    data['year'] and data['year'][0].isdigit() and int(data['year'][0]) == current_year
                ):
                    data['is_same_year'] = True
                else:
                    data['is_same_year'] = False

        pre_added_major = sum(
            data['credit'] for data in candidate_data
            if data['category'] in ['전공필수', '전공선택'] and data.get('pre_added', False)
        )
        
        if pre_added_major < target_major:
            needed_major = target_major - pre_added_major
            available_same_year_elective = sum(
                data['credit'] for data in candidate_data
                if data['category'] == '전공선택' and data.get('is_same_year', False) and not data.get('pre_added', False)
            )
            if available_same_year_elective >= needed_major:
                candidate_data = [
                    data for data in candidate_data
                    if not (data['category'] == '전공선택' and data.get('is_same_year') is False)
                ]
                print("DEBUG: 낮은학년 전공선택 과목 제거 후 candidate_data count =", len(candidate_data))

        # exclude_courses 적용
        if exclude_names:
            print("DEBUG: Applying exclude_courses filter:", exclude_names)
            filtered = []
            for d in candidate_data:
                course_name = d['course_name'].strip()
                should_exclude = False
                
                for exclude_name in exclude_names:
                    exclude_name = exclude_name.strip()
                    if not exclude_name:
                        continue
                    
                    # 정확한 매칭
                    if course_name.lower() == exclude_name.lower():
                        should_exclude = True
                        print(f"DEBUG: Exact match exclusion: '{course_name}' == '{exclude_name}'")
                        break
                    
                    # 부분 매칭
                    if exclude_name.lower() in course_name.lower():
                        should_exclude = True
                        print(f"DEBUG: Partial match exclusion: '{exclude_name}' in '{course_name}'")
                        break
                    
                    # 역방향 부분 매칭
                    if course_name.lower() in exclude_name.lower():
                        should_exclude = True
                        print(f"DEBUG: Reverse partial match exclusion: '{course_name}' in '{exclude_name}'")
                        break
                
                if not should_exclude:
                    filtered.append(d)
                else:
                    print(f"DEBUG: Excluded course: {course_name}")
            
            candidate_data = filtered
            print("DEBUG: after exclude_courses filter:", len(candidate_data))

        # CP-SAT 모델 구성
        model = cp_model.CpModel()
        x = {}
        for data in candidate_data:
            x[data['id']] = model.NewBoolVar(f"course_{data['id']}")

        # 미리 추가된 과목 강제 포함
        for data in candidate_data:
            if data.get('pre_added', False):
                model.Add(x[data['id']] == 1)

        # 학점 제약 조건
        model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data) == target_total)
        model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data if
                      data['category'] in ['전공필수', '전공선택']) == target_major)
        model.Add(sum(data['credit'] * x[data['id']] for data in candidate_data if 
                      get_effective_general_category(course=DummyObj({'effective': data.get('effective_category', None)})) or 
                      data['category'] not in ['전공필수', '전공선택']) == target_elective)

        # 시간표 충돌 제약
        slot_mapping = defaultdict(list)
        for data in candidate_data:
            for sched in data['schedule']:
                day = sched['day']
                for t in sched['times'].split(","):
                    if t.strip().isdigit():
                        slot = int(t.strip()) + 8
                        slot_mapping[(day, slot)].append(data['id'])
        
        for (day, slot), ids in slot_mapping.items():
            model.Add(sum(x[cid] for cid in ids) <= 1)

        # 동일 강의명 제약
        name_groups = defaultdict(list)
        for data in candidate_data:
            name_groups[data['course_name']].append(data['id'])
        for name, ids in name_groups.items():
            model.Add(sum(x[cid] for cid in ids) <= 1)

        # 목적함수: 전공필수 우선, 동일학년 전공선택 우선
        required_priority = sum(
            x[data['id']] for data in candidate_data
            if data['category'] == '전공필수' and (
                data['year'] == "전학년" or (data['year'][0].isdigit() and int(data['year'][0]) <= current_year)
            )
        )
        elective_priority = 0.1 * sum(
            x[data['id']] for data in candidate_data
            if data['category'] == '전공선택' and (
                data['year'] == "전학년" or (data['year'][0].isdigit() and int(data['year'][0]) == current_year)
            )
        )
        model.Maximize(required_priority + elective_priority)

        # Phase 1: 최적 목적함수 값 찾기
        solver = cp_model.CpSolver()
        print("DEBUG: Starting Phase 1 optimization...")
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return JsonResponse({"error": "해결책을 찾지 못했습니다."}, status=500)
        
        best_value = solver.ObjectiveValue()
        print("DEBUG: Phase 1 Best objective =", best_value)

        # Phase 2: 최적값을 강제하고 모든 해 찾기
        model2 = cp_model.CpModel()
        x2 = {}
        for data in candidate_data:
            x2[data['id']] = model2.NewBoolVar(f"course2_{data['id']}")

        # 제약 조건 동일하게 적용
        for data in candidate_data:
            if data.get('pre_added', False):
                model2.Add(x2[data['id']] == 1)

        model2.Add(sum(data['credit'] * x2[data['id']] for data in candidate_data) == target_total)
        model2.Add(sum(data['credit'] * x2[data['id']] for data in candidate_data if
                      data['category'] in ['전공필수', '전공선택']) == target_major)
        model2.Add(sum(data['credit'] * x2[data['id']] for data in candidate_data if 
                      get_effective_general_category(course=DummyObj({'effective': data.get('effective_category', None)})) or 
                      data['category'] not in ['전공필수', '전공선택']) == target_elective)

        for (day, slot), ids in slot_mapping.items():
            model2.Add(sum(x2[cid] for cid in ids) <= 1)
        for name, ids in name_groups.items():
            model2.Add(sum(x2[cid] for cid in ids) <= 1)
        
        # 최적 목적함수 값 강제
        model2.Add(sum(x2[data['id']] for data in candidate_data
                      if data['category'] == '전공필수' and (data['year'] == "전학년" or (
                          data['year'][0].isdigit() and int(data['year'][0]) <= current_year))) == int(best_value))
        
        print("DEBUG: Phase 2 forcing optimal objective =", best_value)

        # 해 수집기
        class TimetableSolutionCollector(cp_model.CpSolverSolutionCallback):
            def __init__(self, x, candidate_data, limit):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self._x = x
                self._candidate_data = {d['id']: d for d in candidate_data}
                self._limit = limit
                self._solutions = []
                self._solution_count = 0

            def OnSolutionCallback(self):
                self._solution_count += 1
                print(f"DEBUG: [Phase 2] Found solution #{self._solution_count}")
                if self._solution_count > self._limit:
                    self.StopSearch()
                    return

                solution = []
                for cid, var in self._x.items():
                    if self.Value(var) == 1:
                        data = self._candidate_data[cid]
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
                            'location': data.get('location', '')
                        })
                self._solutions.append(solution)

            def Solutions(self):
                return self._solutions

        collector2 = TimetableSolutionCollector(x2, candidate_data, limit=50)
        solver2 = cp_model.CpSolver()
        print("DEBUG: Starting Phase 2 search for all solutions...")
        solver2.SearchForAllSolutions(model2, collector2)
        print("DEBUG: Phase 2 search finished. Total solutions:", collector2._solution_count)

        timetables_data = collector2.Solutions()
        print("DEBUG: Total unique solutions found:", len(timetables_data))
        print("DEBUG: --- Timetable Generation End ---")

        result = {
            'progress': '완료',
            'found': len(timetables_data),
            'timetables': timetables_data,
            'message': f"총 {len(timetables_data)}개의 시간표를 찾았습니다." if timetables_data else "조건에 맞는 시간표를 찾지 못했습니다. 조건을 변경해보세요."
        }

        def event_stream():
            yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"

        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


def manage_view(request):
    """시간표 관리 페이지 - 저장된 시간표 목록 조회"""
    user_id = request.user.id if request.user.is_authenticated else 8
    saved_timetables = SavedTimetable.objects.filter(user_id=user_id).order_by('-created_at')
    
    print(f"사용자 {user_id}의 저장된 시간표 개수: {saved_timetables.count()}")
    
    timetables_data = []
    for timetable in saved_timetables:
        courses = []
        
        # 시간표의 모든 과목 가져오기
        for course in timetable.courses.all():
            course_data = {
                'course_id': course.course_id,
                'course_name': course.course_name,
                'credit': course.credits,
                'category': course.category,
                'location': course.location,
                'schedules': []
            }
            
            # 각 과목의 스케줄 정보 가져오기
            for schedule in course.schedules.all():
                course_data['schedules'].append({
                    'day': schedule.day_of_week,
                    'times': schedule.time_slots,
                    'start_time': schedule.start_time,
                    'end_time': schedule.end_time,
                    'location': schedule.location
                })
            
            courses.append(course_data)
        
        timetables_data.append({
            'id': timetable.id,
            'title': timetable.title,
            'created_at': timetable.created_at.strftime('%Y-%m-%d %H:%M'),
            'total_credits': timetable.total_credits,
            'major_credits': timetable.major_credits,
            'elective_credits': timetable.elective_credits,
            'courses': courses
        })
        
        print(f"시간표 로드됨: {timetable.title} ({len(courses)}개 과목)")
    
    # JSON 문자열로 변환
    timetables_json = json.dumps(timetables_data, ensure_ascii=False)
    
    print(f"JSON 데이터 크기: {len(timetables_json)} 문자")

    current_user = {
        'user_id': request.user.id if request.user.is_authenticated else 0,
        'username': request.user.username if request.user.is_authenticated else '익명',
        'is_authenticated': bool(request.user.is_authenticated),
    }
    current_user_json = json.dumps(current_user, ensure_ascii=False)
    
    return render(request, "home/manage.html", {
        'timetables': timetables_data,
        'timetables_json': timetables_json,
        'current_user_json': current_user_json,
    })


@csrf_exempt
def save_timetable(request):
    """시간표 저장 API"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST 요청만 허용됩니다.'}, status=405)
    
    try:
        data = json.loads(request.body)
        courses = data.get('courses', [])
        title = data.get('title', '')
        
        print(f"시간표 저장 요청 받음: {len(courses)}개 과목")
        
        # 사용자 정보 가져오기
        user_id = request.user.id if request.user.is_authenticated else 8
        print(f"사용자 ID: {user_id}")
        
        # 시간표 제목 자동 생성
        if not title or title == '새 시간표':
            count = SavedTimetable.objects.filter(user_id=user_id).count()
            title = f"시간표 {count + 1}"
        
        # 학점 계산
        total_credits = sum(course.get('credit', 0) for course in courses)
        major_credits = sum(course.get('credit', 0) for course in courses 
                          if course.get('category', '') in ['전공필수', '전공선택'])
        elective_credits = total_credits - major_credits
        
        print(f"계산된 학점 - 총: {total_credits}, 전공: {major_credits}, 교양: {elective_credits}")
        
        # 시간표 메인 레코드 생성
        timetable = SavedTimetable.objects.create(
            user_id=user_id,
            title=title,
            semester_year=2025,
            semester_term='1학기',
            total_credits=total_credits,
            major_credits=major_credits,
            elective_credits=elective_credits
        )
        
        print(f"시간표 메인 레코드 생성됨: ID {timetable.id}")
        
        # 시간표 상세 정보 저장
        for course_data in courses:
            course_id = course_data.get('course_id')
            course_name = course_data.get('course_name', '')
            credits = course_data.get('credit', 0)
            category = course_data.get('category', '')
            schedules = course_data.get('schedules', [])
            
            print(f"과목 저장 중: {course_name} ({credits}학점)")
            
            # 첫 번째 스케줄의 location을 기본 location으로 사용
            default_location = ''
            if schedules and len(schedules) > 0:
                default_location = schedules[0].get('location', '')
            
            # 과목 정보 저장
            timetable_course = SavedTimetableCourse.objects.create(
                timetable=timetable,
                course_id=course_id,
                course_name=course_name,
                credits=credits,
                category=category,
                location=default_location,
                user_note=course_data.get('note', ''),
                custom_color=course_data.get('color', '')
            )
            
            print(f"과목 레코드 생성됨: ID {timetable_course.id}")
            
            # 스케줄 정보 저장
            for schedule in schedules:
                day = schedule.get('day', '')
                times = schedule.get('times', '')
                schedule_location = schedule.get('location', default_location)
                
                print(f"스케줄 처리 중: {day} {times} @ {schedule_location}")
                
                # 시작/종료 시간 계산
                if times:
                    try:
                        time_slots = times.split(',')
                        if time_slots:
                            start_hour = int(time_slots[0]) + 8  # 02 -> 10시
                            end_hour = int(time_slots[-1]) + 9   # 04 -> 13시
                            start_time = f"{start_hour:02d}:00"
                            end_time = f"{end_hour:02d}:00"
                        else:
                            start_time = "09:00"
                            end_time = "10:00"
                    except (ValueError, IndexError) as e:
                        print(f"시간 파싱 오류: {e}, times: {times}")
                        start_time = "09:00"
                        end_time = "10:00"
                        times = "01"
                else:
                    start_time = "09:00"
                    end_time = "10:00"
                    times = "01"
                
                schedule_record = SavedTimetableSchedule.objects.create(
                    timetable_course=timetable_course,
                    day_of_week=day,
                    start_time=start_time,
                    end_time=end_time,
                    time_slots=times,
                    location=schedule_location
                )
                
                print(f"스케줄 저장됨: ID {schedule_record.id} - {day} {start_time}-{end_time}")
        
        print(f"시간표 저장 완료: {timetable.title}")
        
        return JsonResponse({
            'success': True,
            'timetable_id': timetable.id,
            'title': timetable.title,
            'message': '시간표가 성공적으로 저장되었습니다.'
        })
        
    except Exception as e:
        print(f"시간표 저장 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'시간표 저장 중 오류가 발생했습니다: {str(e)}'}, status=500)


@csrf_exempt
def delete_timetable(request, timetable_id):
    """시간표 삭제 API"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'DELETE 요청만 허용됩니다.'}, status=405)
    
    try:
        user_id = request.user.id if request.user.is_authenticated else 8
        timetable = SavedTimetable.objects.filter(
            id=timetable_id,
            user_id=user_id
        ).first()
        
        if not timetable:
            return JsonResponse({'error': '시간표를 찾을 수 없습니다.'}, status=404)
        
        print(f"시간표 삭제: {timetable.title} (ID: {timetable_id})")
        timetable.delete()
        
        return JsonResponse({
            'success': True,
            'message': '시간표가 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        print(f"시간표 삭제 오류: {str(e)}")
        return JsonResponse({'error': f'시간표 삭제 중 오류가 발생했습니다: {str(e)}'}, status=500) 