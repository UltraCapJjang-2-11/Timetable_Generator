import os
import json
import mysql.connector  # Replaced Django imports
from mysql.connector import errorcode  # Added for error handling


# MySQL Database Configuration (Update with your credentials)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'dbadmin',
    'password': '1q2w3e4r!',
    'database': 'college_course_db',
    'port': 3306  # Optional, default is 3306
}

# college_info 디렉토리 경로
COLLEGE_INFO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                '../../../college_info')
TARGET_YEAR = 2025
TARGET_TERM = '1학기'  # Semester 테이블의 term 필드 값 형식에 맞춰야 함


def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        return cnx
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
        return None


def insert_course_summary_data():
    """
    college_info 디렉토리의 JSON 파일에서 강의 요약 정보를 읽어
    CourseSumm 테이블에 삽입하거나 업데이트합니다.
    """
    cnx = get_db_connection()
    if not cnx:
        print("데이터베이스 연결에 실패하여 스크립트를 종료합니다.")
        return

    cursor = cnx.cursor()
    semester_id = None

    try:
        # 대상 학기 정보 가져오기 (semester_id)
        query_semester = "SELECT semester_id FROM semester WHERE year = %s AND term = %s"
        cursor.execute(query_semester, (TARGET_YEAR, TARGET_TERM))
        result = cursor.fetchone()
        if result:
            semester_id = result[0]
        else:
            print(f"오류: {TARGET_YEAR}년 {TARGET_TERM} 학기 정보를 Semesters 테이블에서 찾을 수 없습니다.")
            return
    except mysql.connector.Error as err:
        print(f"학기 정보 조회 중 오류 발생: {err}")
        return
    except Exception as e:
        print(f"학기 정보 조회 중 알 수 없는 오류 발생: {e}")
        return

    processed_files = 0
    inserted_count = 0
    updated_count = 0
    error_count = 0
    total_json_files = 0

    for root, dirs, files in os.walk(COLLEGE_INFO_DIR):
        for file_name in files:
            if file_name.endswith(".json"):
                total_json_files += 1
                file_path = os.path.join(root, file_name)
                course_code = None  # Initialize for error reporting
                section = None  # Initialize for error reporting
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # 1. JSON에서 교과목번호(course_code)와 분반번호(section) 가져오기
                    course_info = data.get("강의계획서", {}).get("교과목정보", {})
                    course_code = course_info.get("교과목번호")
                    section = course_info.get("분반번호")


                    # course_code, section을 int로 변환
                    try:
                        course_code = int(course_code)
                        section = int(section)
                    except (ValueError, TypeError):
                        print(
                            f"경고: 교과목번호 또는 분반번호가 정수로 변환되지 않습니다. (course_code={course_code}, section={section}, 파일={file_path})")
                        error_count += 1
                        continue

                    # 요약정보 파싱 (문자열로 저장된 JSON도 처리)
                    summary_info_raw = data.get("요약정보", "")
                    try:
                        summary_info = json.loads(summary_info_raw) if isinstance(summary_info_raw, str) else summary_info_raw
                    except Exception:
                        print(f"경고: {file_path} 파일의 요약정보 파싱 실패")
                        error_count += 1
                        continue

                    course_summarization = summary_info.get("강의요약")
                    group_activity_raw = summary_info.get("조별과제여부")

                    if not course_code or not section or course_summarization is None or group_activity_raw is None:
                        print(f"경고: {file_path} 파일에 필요한 정보(교과목번호, 분반, 강의요약, 조별과제여부)가 부족합니다.")
                        error_count += 1
                        continue

                    group_activity = 'Y' if str(group_activity_raw).upper() == 'Y' else 'N'

                    # Courses 테이블에서 course_id 가져오기
                    course_id = None
                    query_course = ("SELECT course_id FROM Courses "
                                    "WHERE course_code = %s AND section = %s AND semester_id = %s")
                    cursor.execute(query_course, (course_code, section, semester_id))
                    course_result = cursor.fetchone()

                    if not course_result:
                        print(
                            f"경고: Courses 테이블에서 교과목번호 '{course_code}', 분반 '{section}', 학기 ID '{semester_id}'에 해당하는 강의를 찾을 수 없습니다. ({file_path})")
                        error_count += 1
                        continue

                    course_id = course_result[0]

                    # CourseSumm 테이블에 데이터 삽입 또는 업데이트
                    # 먼저 해당 course_id로 데이터가 있는지 확인
                    query_check_summ = "SELECT course_id FROM course_summ WHERE course_id = %s"
                    cursor.execute(query_check_summ, (course_id,))
                    existing_summ = cursor.fetchone()

                    if existing_summ:
                        # 업데이트
                        query_update_summ = ("UPDATE course_summ SET course_summarization = %s, group_activity = %s "
                                             "WHERE course_id = %s")
                        cursor.execute(query_update_summ, (course_summarization, group_activity, course_id))
                        updated_count += 1
                    else:
                        # 삽입
                        query_insert_summ = ("INSERT INTO course_summ (course_id, course_summarization, group_activity) "
                                             "VALUES (%s, %s, %s)")
                        cursor.execute(query_insert_summ, (course_id, course_summarization, group_activity))
                        inserted_count += 1

                    cnx.commit()  # Commit after each successful insert/update
                    processed_files += 1

                except json.JSONDecodeError:
                    print(f"오류: {file_path} 파일이 유효한 JSON 형식이 아닙니다.")
                    error_count += 1
                except mysql.connector.Error as err:
                    print(f"데이터베이스 오류 처리 중 예외 발생 ({file_path}): {err}")
                    cnx.rollback()  # Rollback on error for this file
                    error_count += 1
                except Exception as e:
                    print(f"오류 처리 중 알 수 없는 예외 발생 ({file_path}): {e}")
                    import traceback
                    traceback.print_exc()
                    cnx.rollback()  # Rollback on error for this file
                    error_count += 1

    print(f"\n--- 작업 완료 ---")
    print(f"전체 JSON 파일 수: {total_json_files}")
    print(f"처리된 JSON 파일 수: {processed_files}")
    print(f"새로 삽입된 요약 정보 수: {inserted_count}")
    print(f"업데이트된 요약 정보 수: {updated_count}")
    print(f"오류 발생 수: {error_count}")

    # Close connection
    if cursor:
        cursor.close()
    if cnx and cnx.is_connected():
        cnx.close()
        print("MySQL 연결이 종료되었습니다.")


if __name__ == '__main__':
    print("강의 요약 정보 삽입 스크립트를 시작합니다...")
    insert_course_summary_data()
    print("강의 요약 정보 삽입 스크립트를 종료합니다.")