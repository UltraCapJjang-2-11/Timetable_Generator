import pandas as pd
import os
import re
import mysql.connector
from openpyxl import load_workbook


######################################
# 1) 수업시간 파싱 함수 (변경 없음)
######################################
def parse_class_time(raw_time: str):
    """
    예: "월 02 ,03 [S4-1-101(21-101)]  목 01 [S4-1-101(21-101)]"
    파싱 →
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


######################################
# 2) Read-only 방식으로 엑셀 파일 읽기 (셀 값만 읽음)
######################################
def read_excel_readonly(excel_path, skiprows=2):
    """
    openpyxl을 read_only와 data_only 모드로 사용하여, 엑셀의 셀 값만 읽어 DataFrame으로 반환합니다.
    """
    wb = load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb.active
    data = list(ws.values)[skiprows:]
    df = pd.DataFrame(data)
    return df


######################################
# 3) SEMESTER ID 조회 함수
######################################
def get_semester_id(year, term):
    conn = mysql.connector.connect(
        host="localhost",
        user="dbadmin",
        password="1q2w3e4r!",
        database="college_course_db"
    )
    cursor = conn.cursor()
    query = "SELECT semester_id FROM SEMESTER WHERE year = %s AND term = %s"
    cursor.execute(query, (year, term))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result:
        return result[0]
    else:
        raise ValueError(f"Semester {year} {term} not found in SEMESTER table.")


######################################
# 4) 엑셀 파싱 + DB INSERT 함수 (semester_id 인자 추가)
######################################
def parse_and_insert_to_db(excel_path, semester_id):
    """
    엑셀 파일을 read-only 방식으로 읽어서 스타일 정보 없이 셀의 값만 DataFrame으로 가져온 후,
    파일 이름과 각 행의 값을 기반으로 COURSE 및 COURSE_SCHEDULE 테이블에 데이터를 삽입합니다.
    """
    # (A) 파일 이름 파싱
    file_base = os.path.basename(excel_path)
    file_name, _ = os.path.splitext(file_base)
    tokens = file_name.split('_')

    if tokens[0] == "전공":
        file_type = "전공"
        dept_name = tokens[1]
    elif tokens[0] == "교양":
        file_type = "교양"
        child_category = tokens[2]
        file_class_type = tokens[3] if len(tokens) > 3 else ""
        file_dept_id = 1
    elif tokens[0] == "교직":
        file_type = "교직"
    elif tokens[0] == "일반선택":
        file_type = "일반선택"
    else:
        raise ValueError("파일 이름 형식이 올바르지 않습니다. (전공, 교양, 교직, 일반선택 중 하나여야 합니다.)")

    # (B) 엑셀 파일 읽기 (read-only 방식)
    df = read_excel_readonly(excel_path, skiprows=2)
    # A~V열(총 22개) 가정
    df.columns = [
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
        "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
        "U", "V"
    ]
    df.drop(columns=["A", "M", "N", "O"], inplace=True)
    rename_dict = {
        "B": "year",
        "C": "course_type",  # 전공: "전공필수" 또는 "전공선택"
        "D": "course_code",
        "E": "course_name",
        "F": "section",
        "G": "credit",
        "H": "class_type",  # 교양/교직/일반선택: 필요시 파일명 또는 Excel 값 사용
        "I": "grade_type",
        "J": "foreign_course",
        "K": "instructor",
        "L": "class_time",
        "P": "lecture_hours",
        "Q": "lecture_units",
        "R": "lab_hours",
        "S": "lab_units",
        "T": "pre_enrollment_count",
        "U": "capacity",
        "V": "enrolled_count"
    }
    df.rename(columns=rename_dict, inplace=True)
    df = df.fillna("").astype(str)

    # (C) DB 연결
    conn = mysql.connector.connect(
        host="localhost",
        user="dbadmin",
        password="1q2w3e4r!",
        database="college_course_db"
    )
    cursor = conn.cursor()

    # (D) 학과/카테고리 처리
    if file_type == "전공":
        select_dept_sql = "SELECT dept_id FROM DEPARTMENT WHERE dept_name = %s"
        cursor.execute(select_dept_sql, (dept_name,))
        result = cursor.fetchone()
        if result:
            dept_id = result[0]
        else:
            insert_dept_sql = "INSERT INTO DEPARTMENT (dept_name) VALUES (%s)"
            cursor.execute(insert_dept_sql, (dept_name,))
            dept_id = cursor.lastrowid
            conn.commit()
    elif file_type == "교양":
        dept_id = file_dept_id
        select_cat_sql = "SELECT category_id FROM CATEGORY WHERE category_name = %s"
        cursor.execute(select_cat_sql, (child_category,))
        result = cursor.fetchone()
        if result:
            category_id = result[0]
        else:
            insert_cat_sql = "INSERT INTO CATEGORY (category_name, category_type, description) VALUES (%s, %s, %s)"
            cursor.execute(insert_cat_sql, (child_category, "교양", f"자동입력: {child_category}"))
            category_id = cursor.lastrowid
            conn.commit()
    elif file_type == "교직":
        dept_id = 13
        category_id = 4
    elif file_type == "일반선택":
        dept_id = 14
        category_id = 3
    else:
        raise ValueError("파일 타입이 올바르지 않습니다.")

    # (E) INSERT 쿼리 정의 (COURSE 테이블에 강좌 정적 정보 + 개설정보 삽입)
    insert_course_sql = """
    INSERT INTO COURSE (
        course_code, section, dept_id, category_id, year, course_type, course_name, credit,
        class_type, grade_type, foreign_course, instructor,
        lecture_hours, lecture_units, lab_hours, lab_units,
        semester_id, pre_enrollment_count, capacity, enrolled_count
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s
    )
    """
    # course_id가 자동 생성되므로 lastrowid 사용
    insert_schedule_sql = """
    INSERT INTO COURSE_SCHEDULE (
        course_id, day, times, location
    ) VALUES (%s, %s, %s, %s)
    """

    # (F) 각 행을 순회하며 데이터 INSERT
    for idx, row in df.iterrows():
        year = row["year"]
        if file_type == "전공":
            course_type_val = row["course_type"].strip()
            if course_type_val == "전공필수":
                row_category_id = 5
            elif course_type_val == "전공선택":
                row_category_id = 6
            else:
                raise ValueError(f"알 수 없는 전공 이수구분: {course_type_val}")
            class_type_val = row["class_type"]
        elif file_type == "교양":
            course_type_val = row["course_type"]
            class_type_val = file_class_type
            row_category_id = category_id
        elif file_type == "교직":
            course_type_val = row["course_type"].strip()
            class_type_val = row["class_type"]
            row_category_id = category_id
        elif file_type == "일반선택":
            course_type_val = row["course_type"].strip()
            class_type_val = row["class_type"]
            row_category_id = category_id
        else:
            raise ValueError("파일 타입이 올바르지 않습니다.")

        course_code = row["course_code"]
        course_name = row["course_name"]
        section = row["section"].strip() if row["section"] else "0"
        try:
            credit = int(float(row["credit"])) if row["credit"] else 0
        except:
            credit = 0
        grade_type = row["grade_type"]
        foreign_course = row["foreign_course"]
        instructor = row["instructor"]

        def to_float_or_zero(x):
            try:
                return float(x) if x != "" else 0.0
            except:
                return 0.0

        lecture_hours = to_float_or_zero(row["lecture_hours"])
        lecture_units = to_float_or_zero(row["lecture_units"])
        lab_hours = to_float_or_zero(row["lab_hours"])
        lab_units = to_float_or_zero(row["lab_units"])

        try:
            pre_enrollment_count = int(float(row["pre_enrollment_count"])) if row["pre_enrollment_count"] else 0
        except:
            pre_enrollment_count = 0
        try:
            capacity = int(float(row["capacity"])) if row["capacity"] else 0
        except:
            capacity = 0
        try:
            enrolled_count = int(float(row["enrolled_count"])) if row["enrolled_count"] else 0
        except:
            enrolled_count = 0

        course_vals = (
            course_code,
            section,
            dept_id,
            row_category_id,
            year,
            course_type_val,
            course_name,
            credit,
            class_type_val,
            grade_type,
            foreign_course,
            instructor,
            lecture_hours,
            lecture_units,
            lab_hours,
            lab_units,
            semester_id,
            pre_enrollment_count,
            capacity,
            enrolled_count
        )
        try:
            cursor.execute(insert_course_sql, course_vals)
            course_id = cursor.lastrowid
        except mysql.connector.errors.IntegrityError as e:
            if e.errno == 1062:
                print(f"[중복] COURSE 중복: course_code={course_code}, section={section}, name={course_name}")
                continue
            else:
                raise e

        raw_time_str = row["class_time"]
        time_list = parse_class_time(raw_time_str)
        for tinfo in time_list:
            day = tinfo["day"]
            times_str = ",".join(tinfo["times"])
            location = tinfo["location"]
            schedule_vals = (course_id, day, times_str, location)
            try:
                cursor.execute(insert_schedule_sql, schedule_vals)
            except mysql.connector.errors.IntegrityError as e:
                if e.errno == 1062:
                    print(f"[중복] COURSE_SCHEDULE 중복: course_id={course_id}, day={day}, location={location}")
                else:
                    raise e

    conn.commit()
    cursor.close()
    conn.close()
    print(f"[완료] Excel '{excel_path}' 파싱 → DB 삽입 완료.")


######################################
# 5) 메인: ../target 디렉토리 내의 모든 하위 폴더를 순회하며 처리
######################################
if __name__ == "__main__":
    target_dir = "../target"
    for folder in os.listdir(target_dir):
        folder_path = os.path.join(target_dir, folder)
        if os.path.isdir(folder_path):
            parts = folder.split('_')
            if len(parts) < 2:
                print(f"[오류] 폴더명 형식이 올바르지 않음: {folder}")
                continue
            year_val = parts[0]
            term_val = parts[1]
            try:
                sem_id = get_semester_id(year_val, term_val)
            except ValueError as ve:
                print(ve)
                continue
            for file in os.listdir(folder_path):
                if file.endswith(".xlsx"):
                    excel_file_path = os.path.join(folder_path, file)
                    print(f"처리 중: {excel_file_path} (Semester: {year_val} {term_val}, semester_id={sem_id})")
                    parse_and_insert_to_db(excel_file_path, sem_id)
