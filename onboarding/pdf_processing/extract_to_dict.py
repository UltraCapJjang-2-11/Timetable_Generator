"""

학생의 정보가 담긴 PDF 파일을 전처리 하는 소스코드
원하는 테이블들을 딕셔너리 형태로 만든다

"""

import os
from typing import Dict, Any, List

import pdfplumber                       # PDF의 텍스트, 테이블, 객체 등을 다륨

# '▶' 기호로 시작하는 명확한 라벨이 있는 테이블들의 제목 목록
LABELED_TABLES_TO_FIND = [
    '▶ 이수구분별 취득학점 상세 합계표',
    '▶ 이수구분별 취득학점 합계표',
]

# '학점 이수 현황' 테이블을 식별하기 위한 기준이 되는 헤더(첫 행) 내용
COURSE_HISTORY_HEADER = ['구분', '영역', '세부영역', '년도', '학기', '교과목번호', '교과목명', '학점', '이수구분', '성적']

# --- 함수 정의: 각기 다른 유형의 데이터를 식별하는 전문 함수들 ---
def find_student_info_table_objects(page: pdfplumber.page.Page) -> Dict[str, pdfplumber.table.Table]:
    """
    페이지 상단에서 학생 정보가 포함된 테이블 객체들을 찾습니다.
    이 테이블들은 명확한 라벨이 없으므로, 위치와 내용 기반으로 찾습니다.
    """
    info_tables = {}
    # 페이지의 상단 30% 영역만 잘라서 검색 범위를 제한 -> 다른 테이블과 겹치지 않고 성능 향상
    top_bbox = (0, 0, page.width, page.height * 0.3)
    tables_in_top = page.crop(top_bbox).find_tables()

    # 상단 영역에서 찾은 테이블들을 순회하며 키워드로 구분
    for i, table in enumerate(tables_in_top):
        # .extract()를 호출하여 테이블 내용 중 첫 행, 첫 열의 텍스트만 확인
        first_cell_text = table.extract(x_tolerance=3, y_tolerance=3)[0][0]

        # PDF에서 텍스트 추출 시 글자 사이에 공백이 들어가는 경우가 있으므로 "대 학"으로 확인
        if first_cell_text and "대 학" in first_cell_text:
            info_tables['학생정보_소속대학'] = table
        elif first_cell_text and "과정" in first_cell_text:
            info_tables['학생정보_개인정보0'] = table  # 키를 다르게 하여 여러 정보 블록을 구분
        elif first_cell_text and "학번" in first_cell_text:
            info_tables['학생정보_개인정보1'] = table
        elif first_cell_text and "학년" in first_cell_text:
            info_tables['학생정보_개인정보2'] = table
        elif first_cell_text and "교직\n적용년도" in first_cell_text:  # 줄바꿈 문자(\n)까지 고려
            info_tables['학생정보_개인정보3'] = table

    return info_tables
def find_grade_table_objects(pdf: pdfplumber.PDF) -> pdfplumber.table.Table:
    """
    PDF에서 학생의 성적 정보가 포함된 테이블 객체를 찾습니다.
    이 테이블들은 명확한 라벨이 없으므로, (보통 '이수 구분별 취득학점 상세 합계표' 다음에 위치하긴 하지만)
    특정 키워드를 통해 해당 테이블을 찾습니다.
    """

    for page in pdf.pages:
        page_tables = page.find_tables()

        for i, table in enumerate(page_tables):
            first_cell_text = table.extract()[0][0]

            if first_cell_text and "평 점 계" in first_cell_text:

                return table

    return None
def find_labeled_table_objects(pdf: pdfplumber.PDF) -> Dict[str, pdfplumber.table.Table]:
    """미리 정의된 '▶' 라벨을 기준으로 바로 아래의 테이블 객체를 찾습니다."""
    found_tables = {}
    for page in pdf.pages:
        page_tables = page.find_tables()
        if not page_tables: continue

        for label_text in LABELED_TABLES_TO_FIND:
            # '▶' 문자를 제거하여 깔끔한 이름으로 키를 만듦
            clean_label = label_text.replace('▶', '').strip()
            # 이미 찾은 테이블은 건너뛰어 중복 방지
            if clean_label in found_tables: continue

            # 페이지에서 라벨 텍스트의 위치를 검색
            label_matches = page.search(label_text)
            if not label_matches: continue

            # 라벨의 y좌표(하단 기준)를 가져옴
            label_y = label_matches[0]['bottom']
            closest_table = None
            min_distance = float('inf')

            # 라벨보다 아래에 있는 테이블 중 가장 가까운 테이블을 찾음
            for table in page_tables:
                table_y = table.bbox[1]  # 테이블의 y좌표(상단 기준)
                if table_y > label_y:  # 테이블이 라벨보다 아래에 있는 경우
                    distance = table_y - label_y
                    if distance < min_distance:
                        min_distance = distance
                        closest_table = table

            if closest_table:
                # 찾은 테이블 객체를 딕셔너리에 저장
                found_tables[clean_label] = closest_table
    return found_tables
def find_course_history_table_objects(pdf: pdfplumber.PDF) -> List[pdfplumber.table.Table]:
    """여러 페이지에 걸쳐있을 수 있는 '학점 이수 현황' 테이블을 모두 찾습니다."""
    course_history_tables = []
    # 상태 플래그: '학점이수현황' 테이블의 시작 부분을 찾았는지 여부를 기억
    header_found = False
    for page in pdf.pages:
        tables = page.find_tables()
        if not tables: continue
        for table in tables:
            # 테이블의 첫 행(헤더)만 추출하여 확인
            extracted_header = table.extract(x_tolerance=3, y_tolerance=3)[0]

            # 1. 아직 헤더를 못 찾았고, 현재 테이블의 헤더가 우리가 찾는 헤더와 일치하는 경우
            if not header_found and extracted_header == COURSE_HISTORY_HEADER:
                course_history_tables.append(table)
                header_found = True  # 상태 변경: 이제부터 이어지는 테이블을 찾아야 함

            # 2. 헤더를 이미 찾았고, 현재 테이블이 헤더가 아닌 내용으로만 이뤄진 경우 (이어지는 부분)
            elif header_found and len(extracted_header) == len(COURSE_HISTORY_HEADER):
                # 만약 또 헤더가 나온다면, 다른 종류의 테이블이 시작된 것이므로 탐색 중단
                if extracted_header == COURSE_HISTORY_HEADER:
                    header_found = False
                    break
                # 헤더가 아니면, 이어지는 테이블로 간주하고 목록에 추가
                course_history_tables.append(table)

        # 페이지를 다 돌았는데, 이전에 헤더를 찾았지만 이번 페이지에선 못찾았다면 탐색 종료
        if not header_found and len(course_history_tables) > 0:
            break
    return course_history_tables
def identify_document_objects(file_path: str) -> Dict[str, Any]:
    """
    PDF 문서를 분석하는 총괄 함수.
    각각의 전문 식별 함수들을 호출하여 결과를 딕셔너리로 합친다.
    """
    if not os.path.exists(file_path):
        return {"error": "파일을 찾을 수 없습니다."}

    analysis_map = {}  # 결과를 저장하는 딕셔너리
    with pdfplumber.open(file_path) as pdf:
        first_page = pdf.pages[0]

        analysis_map.update(find_student_info_table_objects(first_page))    # 학생 개인정보는 1페이지만 (보통 그러므로)
        analysis_map.update(find_labeled_table_objects(pdf))                # 라벨 기반의 테이블 찾기
        analysis_map['성적정보'] = find_grade_table_objects(pdf)             # 성적 요약 정보 테이블
        analysis_map['학점이수현황'] = find_course_history_table_objects(pdf)  # 학점 이수현황 테이블

    return analysis_map


