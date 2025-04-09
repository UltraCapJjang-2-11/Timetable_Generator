import pandas as pd
import os
import re
import mysql.connector

######################################
# 1) 수업시간 파싱 함수
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
# 2) 엑셀 파싱 + DB INSERT 함수
######################################
def parse_and_insert_to_db(excel_path):
    
    """
    1) 엑셀 파일(헤더는 1·2행, 3행부터 실제 정보) 파싱
    2) 파일 이름으로부터 개설강의목록 정보를 추출하여:
       - 전공: 파일명 형식은 "전공_학과명"으로 시작하며,
         각 행의 "이수구분" 열(Excel의 course_type)을 확인하여,
         "전공필수"이면 category_id=5, "전공선택"이면 category_id=6로 결정.
         → DEPARTMENT 테이블에서 학과 조회(없으면 INSERT) 후 dept_id 결정.
       - 교양: 파일명 형식은 "교양_상위카테고리_최하위카테고리_이수구분"으로 되어 있으며,
         dept_id는 1, 최하위 카테고리(child_category)는 파일명에서, 강의구분은 네번째 토큰으로 결정하고,
         CATEGORY 테이블에서 최하위 카테고리를 조회(없으면 INSERT)하여 category_id 결정.
       - 교직: 파일명은 "교직"으로 시작 → dept_id는 13, category_id는 4.
       - 일반선택: 파일명은 "일반선택"으로 시작 → dept_id는 14, category_id는 3.
    3) 각 강좌 정보를 DB에 INSERT (COURSE, COURSE_SCHEDULE, COURSE_OFFERING)
       - semester_id는 하드코딩된 값 사용.
    만약 PRIMARY KEY가 겹치는 경우, 해당 예외를 잡아 어떤 키가 중복되었는지 출력합니다.
    """
    # (A) 파일 이름 파싱
    file_base = os.path.basename(excel_path)
    file_name, _ = os.path.splitext(file_base)
    tokens = file_name.split('_')

    # 파일 이름의 첫 토큰으로 파일 종류 결정
    if tokens[0] == "전공":
        file_type = "전공"
        dept_name = tokens[1]  # 예: "전공_소프트웨어학과"
    elif tokens[0] == "교양":
        file_type = "교양"
        child_category = tokens[2]   # 예: "교양_개신기초교양_의사소통_일반"
        file_class_type = tokens[3] if len(tokens) > 3 else ""
        file_dept_id = 1
    elif tokens[0] == "교직":
        file_type = "교직"
    elif tokens[0] == "일반선택":
        file_type = "일반선택"
    else:
        raise ValueError("파일 이름 형식이 올바르지 않습니다. (전공, 교양, 교직, 일반선택 중 하나여야 합니다.)")

    # (B) 엑셀 파일 읽기
    df = pd.read_excel(excel_path, skiprows=2, header=None)
    df.columns = [
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
        "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
        "U", "V"
    ]
    df.drop(columns=["A", "M", "N", "O"], inplace=True)
    rename_dict = {
        "B": "year",
        "C": "course_type",  # Excel 내부의 값 (전공인 경우 "전공필수" 또는 "전공선택")
        "D": "course_code",
        "E": "course_name",
        "F": "section",
        "G": "credit",
        "H": "class_type",   # 교양, 교직, 일반선택의 경우 필요하면 파일명 또는 Excel 값 사용
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

    # (D) 학과 및 카테고리 처리
    if file_type == "전공":
        # 전공: DEPARTMENT 테이블에서 학과 조회 (없으면 INSERT)
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
        # 각 행의 "이수구분" 열 값에 따라 category_id 결정 (전공필수 → 5, 전공선택 → 6)
    elif file_type == "교양":
        file_dept_id = 1
        # DEPARTMENT 테이블에 dept_id=1인 부서가 있는지 확인
        cursor.execute("SELECT dept_id FROM DEPARTMENT WHERE dept_id = %s", (file_dept_id,))
        if cursor.fetchone() is None:
            insert_dept_sql = "INSERT INTO DEPARTMENT (dept_id, dept_name) VALUES (%s, %s)"
            cursor.execute(insert_dept_sql, (file_dept_id, "교양학부"))
            conn.commit()
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
        dept_candidate = 13
        # DEPARTMENT 테이블에 dept_id=13인 부서가 있는지 확인
        cursor.execute("SELECT dept_id FROM DEPARTMENT WHERE dept_id = %s", (dept_candidate,))
        if cursor.fetchone() is None:
            insert_dept_sql = "INSERT INTO DEPARTMENT (dept_id, dept_name) VALUES (%s, %s)"
            cursor.execute(insert_dept_sql, (dept_candidate, "교직학부"))
            conn.commit()
        dept_id = dept_candidate
        category_id = 4

    elif file_type == "일반선택":
        dept_candidate = 14
        # DEPARTMENT 테이블에 dept_id=14인 부서가 있는지 확인
        cursor.execute("SELECT dept_id FROM DEPARTMENT WHERE dept_id = %s", (dept_candidate,))
        if cursor.fetchone() is None:
            insert_dept_sql = "INSERT INTO DEPARTMENT (dept_id, dept_name) VALUES (%s, %s)"
            cursor.execute(insert_dept_sql, (dept_candidate, "일반선택학부"))
            conn.commit()
        dept_id = dept_candidate
        category_id = 3

    else:
        raise ValueError("파일 타입이 올바르지 않습니다.")

    # (E) 하드코딩: 학기 id
    hardcoded_semester_id = 21

    # (F) INSERT 쿼리 정의 (COURSE, COURSE_SCHEDULE, COURSE_OFFERING)
    insert_course_sql = """
    INSERT INTO COURSE (
        course_code, section, dept_id, category_id, year, course_type, course_name, credit,
        class_type, grade_type, foreign_course, instructor,
        lecture_hours, lecture_units, lab_hours, lab_units
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s
    )
    """
    insert_schedule_sql = """
    INSERT INTO COURSE_SCHEDULE (
        course_code, section, day, times, location
    ) VALUES (%s, %s, %s, %s, %s)
    """
    insert_offering_sql = """
    INSERT INTO COURSE_OFFERING (
        course_code, section, semester_id, pre_enrollment_count, capacity, enrolled_count
    ) VALUES (%s, %s, %s, %s, %s, %s)
    """

    # (G) 각 행을 순회하며 데이터 INSERT
    for idx, row in df.iterrows():
        year = row["year"]
        # 파일 타입별로 처리: 전공/교양는 Excel의 이수구분을 기준으로, 교직/일반선택은 고정값 사용
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
            course_type_val = row["course_type"].strip()  # Excel 값 사용 (필요에 따라 조정 가능)
            class_type_val = row["class_type"]
            row_category_id = category_id  # 4
        elif file_type == "일반선택":
            course_type_val = row["course_type"].strip()
            class_type_val = row["class_type"]
            row_category_id = category_id  # 3
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

        # INSERT COURSE
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
            lab_units
        )
        try:
            cursor.execute(insert_course_sql, course_vals)
        except mysql.connector.errors.IntegrityError as e:
            if e.errno == 1062:
                print(f"[중복] COURSE 중복: course_code={course_code}, section={section}, name={course_name}")
                continue
            else:
                raise e

        # INSERT COURSE_SCHEDULE
        raw_time_str = row["class_time"]
        time_list = parse_class_time(raw_time_str)
        for tinfo in time_list:
            day = tinfo["day"]
            times_str = ",".join(tinfo["times"])
            location = tinfo["location"]
            schedule_vals = (course_code, section, day, times_str, location)
            try:
                cursor.execute(insert_schedule_sql, schedule_vals)
            except mysql.connector.errors.IntegrityError as e:
                if e.errno == 1062:
                    print(f"[중복] COURSE_SCHEDULE 중복: course_code={course_code}, section={section}, day={day}, location={location}")
                else:
                    raise e

        # 동적 정보 숫자형 변환
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

        # INSERT COURSE_OFFERING
        offering_vals = (
            course_code,
            section,
            hardcoded_semester_id,
            pre_enrollment_count,
            capacity,
            enrolled_count
        )
        try:
            cursor.execute(insert_offering_sql, offering_vals)
        except mysql.connector.errors.IntegrityError as e:
            if e.errno == 1062:
                print(f"[중복] COURSE_OFFERING 중복: course_code={course_code}, section={section}, semester_id={hardcoded_semester_id}")
            else:
                raise e

    conn.commit()
    cursor.close()
    conn.close()
    print(f"[완료] Excel '{excel_path}' 파싱 → DB 삽입 완료.")

######################################
# 3) 메인: ../target 디렉토리 내의 모든 .xlsx 파일 처리 (모든 파일이 개설강의목록 파일임)
######################################
if __name__ == "__main__":
    target_dir = r"C:\Users\User\Desktop\fit\Timetable_Generator-main\db\target"
    for file in os.listdir(target_dir):
        if file.endswith(".xlsx"):
            excel_file_path = os.path.join(target_dir, file)
            print(f"처리 중: {excel_file_path}")
            parse_and_insert_to_db(excel_file_path)
