import os
import json
import pymysql

# DB 연결 설정 (실제 환경에 맞게 수정)
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "dbadmin"
DB_PASSWORD = "1q2w3e4r!"
DB_NAME = "college_course_db"

# 기본 대학 (예: 충북대학교)
UNIVERSITY_NAME = "충북대학교"

def get_db_connection():
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )
    return conn


def get_university_id(conn, university_name):
    with conn.cursor() as cursor:
        sql = "SELECT university_id FROM Universities WHERE university_name = %s"
        cursor.execute(sql, (university_name,))
        result = cursor.fetchone()
        return result["university_id"] if result else None


def get_semester_id(conn, year, term):
    with conn.cursor() as cursor:
        sql = "SELECT semester_id FROM SEMESTER WHERE year = %s AND term = %s"
        cursor.execute(sql, (year, term))
        result = cursor.fetchone()
        return result["semester_id"] if result else None


def get_college_id(conn, university_id, college_name):
    with conn.cursor() as cursor:
        sql = "SELECT college_id FROM Colleges WHERE university_id = %s AND college_name = %s"
        cursor.execute(sql, (university_id, college_name))
        result = cursor.fetchone()
        return result["college_id"] if result else None


def get_department_id(conn, university_id, college_id, dept_name):
    with conn.cursor() as cursor:
        sql = "SELECT dept_id FROM Departments WHERE university_id = %s AND dept_name = %s AND college_id = %s"
        cursor.execute(sql, (university_id, dept_name, college_id))
        result = cursor.fetchone()
        return result["dept_id"] if result else None


def get_major_id(conn, dept_id, major_name):
    with conn.cursor() as cursor:
        sql = "SELECT major_id FROM Major WHERE dept_id = %s AND major_name = %s"
        cursor.execute(sql, (dept_id, major_name))
        result = cursor.fetchone()
        return result["major_id"] if result else None


def get_category_id(conn, category_name, version_year):
    with conn.cursor() as cursor:
        sql = "SELECT category_id FROM Category WHERE category_name = %s AND version_year = %s"
        cursor.execute(sql, (category_name, version_year))
        result = cursor.fetchone()
        return result["category_id"] if result else None


def insert_course(conn, dept_id, major_id, category_id, semester_id, course):
    with conn.cursor() as cursor:
        sql = """
            INSERT INTO Courses
            (dept_id, major_id, category_id, semester_id, course_name, course_code, section, credits, target_year, grade_type, foreign_course, instructor_name, lecture_hours, lecture_times, lab_hours, lab_times, pre_enrollment_count, capacity, enrolled_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            dept_id,
            major_id,
            category_id,
            semester_id,
            course["course_name"],
            course["course_code"],
            course["section"],
            int(course["credit"]) if course["credit"] is not None else 0,
            str(course["target_year"]),
            course["grade_type"],
            course["foreign_course"],
            course["instructor_name"],
            float(course["lecture_hours"]) if course["lecture_hours"] is not None else 0.0,
            float(course["lecture_times"]) if course["lecture_times"] is not None else 0.0,
            float(course["lab_hours"]) if course["lab_hours"] is not None else 0.0,
            float(course["lab_times"]) if course["lab_times"] is not None else 0.0,
            int(course["pre_enrollment_count"]) if course["pre_enrollment_count"] is not None else 0,
            int(course["capacity"]) if course["capacity"] is not None else 0,
            int(course["enrolled_count"]) if course["enrolled_count"] is not None else 0
        ))
        return cursor.lastrowid



def insert_course_schedule(conn, course_id, schedule):
    with conn.cursor() as cursor:
        # times는 리스트를 콤마로 join
        times_str = ",".join(schedule.get("times", []))
        sql = """
            INSERT INTO COURSE_SCHEDULES (course_id, day, times, location)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql, (course_id, schedule["day"], times_str, schedule["location"]))


def process_json_file(conn, json_filepath):
    """
    하나의 JSON 파일을 처리합니다.
    필요한 외부키를 조회한 후, Courses와 COURSE_SCHEDULES에 데이터를 삽입합니다.
    문제 발생 시 오류를 기록하고, 파일 처리는 건너뜁니다.
    반환: (삽입된 강의 개수, 오류 메시지 리스트)
    """
    error_messages = []
    inserted_courses_count = 0

    # JSON 파일 로드
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        error_messages.append(f"{json_filepath}: JSON 로드 실패 - {e}")
        return 0, error_messages

    # 메타정보 읽기
    try:
        year = int(data["year"])
        term = data["term"]  # 예: "1학기"
        college_name = data["college"]
        dept_name = data["department"]
        major_name = data["major"]
    except Exception as e:
        error_messages.append(f"{json_filepath}: 메타정보 파싱 실패 - {e}")
        return 0, error_messages

    # Semester 조회
    semester_id = get_semester_id(conn, year, term)
    if semester_id is None:
        error_messages.append(f"{json_filepath}: Semester not found for year {year} and term {term}.")
        return 0, error_messages

    # University 조회 (기본 대학)
    university_id = get_university_id(conn, UNIVERSITY_NAME)
    if university_id is None:
        error_messages.append(f"{json_filepath}: University '{UNIVERSITY_NAME}' not found.")
        return 0, error_messages

    # 전공 파일인 경우 College, Department, Major 조회 (비분류가 아니면)
    dept_id = None
    major_id = None
    if college_name != "비분류":
        college_id = get_college_id(conn, university_id, college_name)
        if college_id is None:
            error_messages.append(f"{json_filepath}: College '{college_name}' not found.")
            return 0, error_messages
        dept_id = get_department_id(conn, university_id, college_id, dept_name)
        if dept_id is None:
            error_messages.append(f"{json_filepath}: Department '{dept_name}' not found in college '{college_name}'.")
            return 0, error_messages
        if major_name != "비분류":
            major_id = get_major_id(conn, dept_id, major_name)
            if major_id is None:
                error_messages.append(f"{json_filepath}: Major '{major_name}' not found in department '{dept_name}'.")
                return 0, error_messages

    # 강의 데이터 처리
    courses = data["courses"]
    for course in courses:
        # Category 조회 (version_year는 JSON의 year로 사용)
        category_name = course["category"]
        category_id = get_category_id(conn, category_name, 2020)
        if category_id is None:
            error_messages.append(f"{json_filepath}: Category '{category_name}' not found for version year {2020}.")
            return 0, error_messages

        try:
            # Courses 테이블 삽입
            course_id = insert_course(conn, dept_id, major_id, category_id, semester_id, course)
            # 각 강의의 수업시간 정보 삽입 (COURSE_SCHEDULES 테이블)
            for schedule in course.get("class_time", []):
                insert_course_schedule(conn, course_id, schedule)
            inserted_courses_count += 1
        except Exception as e:
            error_messages.append(f"{json_filepath}: Error inserting course with code {course.get('course_code')}: {e}")
            conn.rollback()
            return 0, error_messages

    conn.commit()
    print(f"{json_filepath}: 파일 내 강의 수 (삽입): {inserted_courses_count}")
    return inserted_courses_count, error_messages


def main():
    result_dir = "result"
    error_report = []
    total_inserted = 0

    json_files = [f for f in os.listdir(result_dir) if f.endswith(".json")]
    conn = get_db_connection()
    try:
        for json_file in json_files:
            json_filepath = os.path.join(result_dir, json_file)
            print(f"Processing {json_filepath}...")
            inserted_count, errors = process_json_file(conn, json_filepath)
            total_inserted += inserted_count
            if errors:
                error_report.extend(errors)
            else:
                print(f"{json_file}: Inserted {inserted_count} courses successfully.")
    finally:
        conn.close()

    # error_report.txt에 오류 내용 기록
    if error_report:
        with open("error_report.txt", "w", encoding="utf-8") as f:
            for error in error_report:
                f.write(error + "\n")
        print("Errors occurred during processing. See 'error_report.txt' for details.")
    else:
        print("All files processed successfully.")

    # 마지막에 전체 삽입된 강의 개수 출력
    print(f"총 처리한 강의 개수: {total_inserted}")


if __name__ == "__main__":
    main()
