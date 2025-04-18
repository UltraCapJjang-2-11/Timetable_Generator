import os
import re
import json
import pandas as pd

# 1. 파일명 파싱 함수
def parse_filename(filename: str) -> dict:
    """
    파일명 규칙에 따라 메타정보 추출
    전공, 교양, 일선, 교직 유형을 모두 처리.

    전공 예: 2025_1_전공_전자정보대학_소프트웨어학부_인공지능전공.xlsx
    교양 예: 2025_1_교양_개신기초교양_인성과비판적사고.xlsx
    일선 예: 2025_1_일선.xlsx
    교직 예: 2025_1_교직.xlsx
    """
    base, _ = os.path.splitext(filename)
    parts = base.split('_')

    metadata = {}
    try:
        metadata["year"] = parts[0]  # 예: 2025
        metadata["term"] = parts[1] + "학기"  # 예: 1학기
    except (ValueError, IndexError):
        raise ValueError(f"파일명 {filename}의 년도/학기 정보 파싱 실패")

    # 기본값: 전공 외에는 college, department, major는 "비분류"
    metadata["college"] = "비분류"
    metadata["department"] = "비분류"
    metadata["major"] = "비분류"
    metadata["type"] = parts[2]  # '전공', '교양', '일선', '교직'

    if metadata["type"] == "전공":
        # 전공의 경우: {년도}_{학기}_전공_{단과대학}_{학과(부)}_{전공(optional)}
        if len(parts) >= 5:
            metadata["college"] = parts[3]
            metadata["department"] = parts[4]
        if len(parts) >= 6:
            metadata["major"] = parts[5]
    elif metadata["type"] == "교양":
        # 교양의 경우: {년도}_{학기}_교양_{영역}_{분야(optional)}
        # 교양 파일은 college, department, major는 "비분류"로 유지.
        if len(parts) >= 4:
            # 영역이 기본값, 분야가 있으면 category로 사용.
            metadata["category"] = parts[3] if len(parts) == 4 else parts[4]
    elif metadata["type"] in ("일선", "교직"):
        # 해당 유형은 모두 college, department, major는 "비분류"이고, category는 type 값과 동일하게 처리.
        metadata["category"] = metadata["type"]
    return metadata


# 2. 수업시간 파싱 함수
def parse_class_time(raw_time: str) -> list:
    """
    예: "월 02 ,03 [S4-1-101(21-101)]  목 01 [S4-1-101(21-101)]"
    파싱 결과:
    [
      {"day": "월", "times": ["02", "03"], "location": "S4-1-101(21-101)"},
      {"day": "목", "times": ["01"],       "location": "S4-1-101(21-101)"}
    ]
    """
    if not raw_time or not isinstance(raw_time, str):
        return []
    pattern = r"([월화수목금토일])\s+([\d,\s]+)\s*\[([^\]]+)\]"
    matches = re.findall(pattern, raw_time)
    result = []
    for day, time_str, location in matches:
        times = [t.strip() for t in time_str.split(',') if t.strip()]
        result.append({
            "day": day,
            "times": times,
            "location": location
        })
    return result


# 3. XLSX 파일 파싱 함수 (열 순서 기반 매핑, 결측치는 None으로 처리)
def parse_xlsx(file_path: str) -> list:
    """
    pandas를 사용하여 XLSX 파일을 읽고, 열 순서를 기반으로
    지정된 필드에 매핑한 후 각 행을 강의 정보 객체로 변환.

    1행~2행은 데이터 라벨이므로, 3행부터 읽어야 합니다.
    """
    # header=None: 헤더 없이 숫자 인덱스로 읽고, skiprows=2로 3행부터 데이터 읽기
    df = pd.read_excel(file_path, engine="openpyxl", skiprows=2, header=None)

    # 열 순서 기반 매핑 (총 22열, 생략할 열은 None으로 지정)
    # A:order, B:target_year, C:course_type, D:course_code, E:course_name, F:section, G:credit,
    # H:skip, I:grade_type, J:foreign_course, K:instructor_name, L:class_time,
    # M:skip, N:skip, O:skip, P:lecture_hours, Q:lecture_times, R:lab_hours, S:lab_times,
    # T:pre_enrollment_count, U:capacity, V:enrolled_count
    col_mapping = [
        "order",             # index 0 (A)
        "target_year",       # index 1 (B)
        "course_type",       # index 2 (C)
        "course_code",       # index 3 (D)
        "course_name",       # index 4 (E)
        "section",           # index 5 (F)
        "credit",            # index 6 (G)
        None,                # index 7 (H) - 건너뜀
        "grade_type",        # index 8 (I)
        "foreign_course",    # index 9 (J)
        "instructor_name",   # index 10 (K)
        "class_time",        # index 11 (L)
        None,                # index 12 (M)
        None,                # index 13 (N)
        None,                # index 14 (O)
        "lecture_hours",     # index 15 (P)
        "lecture_times",     # index 16 (Q)
        "lab_hours",         # index 17 (R)
        "lab_times",         # index 18 (S)
        "pre_enrollment_count",  # index 19 (T)
        "capacity",          # index 20 (U)
        "enrolled_count"     # index 21 (V)
    ]

    courses = []
    # 각 행마다 col_mapping을 이용하여 딕셔너리 생성
    for _, row in df.iterrows():
        course = {}
        for idx, key in enumerate(col_mapping):
            if key is not None:
                value = row[idx]
                # 결측치인 경우 None으로 처리
                if pd.isna(value):
                    course[key] = None
                else:
                    course[key] = value
        # class_time은 파싱 함수 적용
        course["class_time"] = parse_class_time(course.get("class_time", ""))
        courses.append(course)
    return courses


# 4. JSON 저장 함수
def save_json(data: dict, filepath: str):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# 5. 메인 프로세스 함수 (DB 삽입 관련 부분은 별도 구현 예정)
def process_file(file_path: str) -> tuple:
    """
    파일을 처리하고, 해당 파일의 강의 개수를 반환합니다.
    추가로, 파일의 마지막 '순번(order)'를 읽어 파일 내에 명시된 총 강의 개수(expected)
    와 실제 처리된 강의 수(actual)를 함께 반환합니다.
    """
    # 1. 파일명 파싱
    metadata = parse_filename(os.path.basename(file_path))

    # 2. XLSX 파일 파싱
    courses = parse_xlsx(file_path)

    # 파일 유형에 따라 강의의 category 설정
    file_type = metadata.get("type")
    if file_type == "교양":
        category = metadata.get("category", "비분류")
        for course in courses:
            course["category"] = category
    elif file_type in ("일선", "교직"):
        for course in courses:
            course["category"] = file_type
    elif file_type == "전공":
        # 전공인 경우 course_type에 따라 category를 설정 ("전공필수" 또는 "전공선택")
        for course in courses:
            course["category"] = course.get("course_type", "비분류")

    # 3. JSON 결과 구성
    result_data = {
        "year": metadata["year"],
        "term": metadata["term"],
        "college": metadata.get("college", "비분류"),
        "department": metadata.get("department", "비분류"),
        "major": metadata.get("major", "비분류"),
        "courses": courses
    }

    # 4. 결과 JSON 저장 (result 디렉토리 생성 여부 확인)
    result_dir = "result"
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    result_filename = os.path.splitext(os.path.basename(file_path))[0] + ".json"
    save_json(result_data, os.path.join(result_dir, result_filename))
    print(f"Processed {file_path} -> {os.path.join(result_dir, result_filename)}")

    # 파일 내 강의 목록에서 마지막 '순번(order)'를 전체 강의 수(expected)로 가정
    if courses:
        try:
            expected_count = int(courses[-1]["order"])
        except Exception:
            expected_count = 0
    else:
        expected_count = 0
    actual_count = len(courses)

    print(f"파일의 총 강의 수(순번 기준): {expected_count}, 실제 처리된 강의 수: {actual_count}\n")
    return actual_count, expected_count


def main():
    target_dir = '../target'
    total_actual = 0
    total_expected = 0
    for filename in os.listdir(target_dir):
        if filename.endswith(".xlsx"):
            file_path = os.path.join(target_dir, filename)
            actual, expected = process_file(file_path)
            total_actual += actual
            total_expected += expected
    print(f"전체 파일에 대한 총 강의 수(순번 기준): {total_expected}, 처리된 강의 수: {total_actual}")


if __name__ == "__main__":
    main()
