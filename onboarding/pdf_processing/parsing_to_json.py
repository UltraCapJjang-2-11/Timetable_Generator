# parsing_to_json.py

import re
from typing import Dict, List, Any, Optional


# --- 맞춤형 파서 함수들 ---

def parse_student_info_tables(tables_dict: Dict[str, List[List[str]]]) -> Dict[str, Optional[str]]:
    """학생 정보 관련 테이블들의 데이터를 파싱하여 하나의 딕셔너리로 통합합니다."""
    parsed_data = {}
    for table_data in tables_dict.values():
        for row in table_data:
            for i in range(0, len(row), 2):
                if i + 1 < len(row):
                    raw_key, raw_value = row[i], row[i + 1]
                    if not raw_key: continue
                    key = re.sub(r'[\s\n]+', '', raw_key)
                    if '(' in raw_key: key = raw_key.strip()
                    value = None
                    if raw_value and raw_value.strip():
                        match = re.match(r'^\s*(\S+)', raw_value.strip())
                        value = match.group(1) if match else raw_value.strip()
                    if key: parsed_data[key] = value
    return parsed_data


def parse_credit_summary_table(raw_data: List[List[str]]) -> Dict[str, Any]:
    """'이수구분별 취득학점 상세 합계표'를 파싱합니다."""
    if not raw_data or len(raw_data) < 5: return {"error": "Data is invalid"}
    headers = ["구분", "교양_개신기초", "교양_자연ㆍ이공기초", "교양_일반", "교양_확대", "교양_OCU기타", "일반선택", "전공_필수", "전공_선택", "부전공_필수",
               "부전공_선택", "다전공1_필수", "다전공1_선택", "다전공1_교직", "다전공2_필수", "다전공2_선택", "다전공2_교직", "교직_이론", "교직_소양", "교직_실습",
               "총계_졸업이수학점"]
    data, (crit_row, earn_row, total_row) = {}, raw_data[2:5]

    def to_int(v):
        return int(re.sub(r'[^0-9]', '', v)) if v and v.strip() else None

    for i, h in enumerate(headers[1:], 1):
        m_key, s_key = (h.split('_') + [None])[:2]
        data.setdefault(m_key, {})
        if s_key:
            data[m_key].setdefault('졸업기준학점', {})[s_key] = to_int(crit_row[i])
            data[m_key].setdefault('이수학점', {})[s_key] = to_int(earn_row[i])
        else:
            data[m_key]['졸업기준학점'], data[m_key]['이수학점'] = to_int(crit_row[i]), to_int(earn_row[i])
    for k, idx in {'교양': 1, '전공': 7, '부전공': 9, '다전공1': 11, '다전공2': 14, '교직': 17}.items():
        if k in data: data[k]['계'] = to_int(total_row[idx])
    return data


def parse_simple_credit_summary(raw_data: List[List[str]]) -> Dict[str, int]:
    """'이수구분별 취득학점 합계표'를 파싱합니다."""
    if not raw_data or len(raw_data) < 2: return {"error": "Data is invalid"}
    return {h: int(v) for h, v in zip(raw_data[0], raw_data[1])}


def parse_grade_info(raw_data: List[List[str]]) -> Dict[str, Optional[str]]:
    """'성적정보' 테이블을 파싱합니다."""
    return parse_student_info_tables({'성적정보': raw_data})  # 학생정보 파서 재사용


def parse_course_history(raw_data_list: List[List[List[str]]]) -> List[Dict[str, str]]:
    """'학점이수현황' 테이블 데이터를 파싱합니다. (셀 병합 처리 포함)"""
    if not raw_data_list: return []
    headers, all_rows, parsed_courses, last_vals = raw_data_list[0][0], [], [], {}
    all_rows.extend(raw_data_list[0][1:])
    for table_data in raw_data_list[1:]: all_rows.extend(table_data)
    for row in all_rows:
        course, i = {}, 0
        for h, cell in zip(headers, row):
            val = cell.replace('\n', ' ') if cell and cell.strip() != '' else last_vals.get(h, '') if i < 3 else ''

            if h == '교과목번호':
                try:
                    course[h] = int(val)
                except (ValueError, TypeError):
                    course[h] = None
            else:
                # 다른 모든 헤더는 기존 방식대로 문자열로 저장
                course[h] = val

            if i < 3 and val != '': last_vals[h] = val
            i += 1
        parsed_courses.append(course)
    return parsed_courses


# --- 총괄 파싱 함수 ---

def create_json_from_identified_objects(identified_objects: Dict[str, Any]) -> Dict[str, Any]:
    """
    식별된 객체 딕셔너리를 받아, 각 객체에 맞는 파서를 호출하여
    최종 JSON 구조를 생성합니다.
    """
    final_json = {}

    # 1. 학생 정보 파싱
    student_info_tables = {k: v.extract() for k, v in identified_objects.items() if k.startswith('학생정보')}
    if student_info_tables: final_json['학생정보'] = parse_student_info_tables(student_info_tables)

    # 2. 상세 학점표 파싱
    table_obj = identified_objects.get('이수구분별 취득학점 상세 합계표')
    if table_obj: final_json['이수구분별취득학점상세'] = parse_credit_summary_table(table_obj.extract())

    # 3. 간단 학점표 파싱
    table_obj = identified_objects.get('이수구분별 취득학점 합계표')
    if table_obj: final_json['이수구분별취득학점합계'] = parse_simple_credit_summary(table_obj.extract())

    # 4. 성적 정보 파싱
    table_obj = identified_objects.get('성적정보')
    if table_obj: final_json['성적정보'] = parse_grade_info(table_obj.extract())

    # 5. 학점 이수 현황 파싱
    table_obj_list = identified_objects.get('학점이수현황')
    if table_obj_list:
        raw_data_list = [t.extract() for t in table_obj_list]
        final_json['학점이수현황'] = parse_course_history(raw_data_list)

    return final_json