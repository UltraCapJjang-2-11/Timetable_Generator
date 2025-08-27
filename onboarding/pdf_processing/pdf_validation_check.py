import pdfplumber
import os

# --- 검증에 사용할 문서의 고유 특징 (지문) 정의 ---

# 1. 문서의 제목 및 기관명 (반드시 포함되어야 함)
MAIN_TITLE = "수강신청을 위한 학점이수 현황"
UNIVERSITY_NAME = "충북대학교"

# 2. 특정 테이블의 헤더 (구조적 특징)
COURSE_HISTORY_HEADER = ['구분', '영역', '세부영역', '년도', '학기', '교과목번호', '교과목명', '학점', '이수구분', '성적']

# 3. 반드시 존재해야 하는 텍스트 라벨
REQUIRED_LABELS = ["▶ 이수구분별 취득학점 상세 합계표"]

# 4. 특정 테이블 내에 반드시 존재해야 하는 키워드
REQUIRED_TABLE_KEYWORDS = ["학번"]


def validate_pdf_format(file_path: str) -> bool:
    """
    입력된 PDF가 우리가 파싱하고자 하는 '학점이수 현황' 문서 형식인지
    다중 검증을 통해 판별합니다.

    Args:
        file_path (str): 검증할 PDF 파일의 경로

    Returns:
        bool: 올바른 형식이면 True, 아니면 False를 반환합니다.
    """

    #print(f"--- '{os.path.basename(file_path)}' 파일 형식 검증 시작 ---")

    try:
        with pdfplumber.open(file_path) as pdf:
            # --- 1단계: 핵심 텍스트 검증 ---
            if not pdf.pages:
                #print("-> [판정 실패] PDF에 페이지가 없습니다.")
                return False

            page1_text = pdf.pages[0].extract_text()
            if not page1_text:
                #print("-> [판정 실패] 첫 페이지에서 텍스트를 추출할 수 없습니다.")
                return False

            if MAIN_TITLE not in page1_text:
                #print(f"-> [판정 실패] 메인 타이틀 '{MAIN_TITLE}'을 찾을 수 없습니다.")
                return False

            if UNIVERSITY_NAME not in page1_text:
                #print(f"-> [판정 실패] 기관명 '{UNIVERSITY_NAME}'을 찾을 수 없습니다.")
                return False


            #print("-> 1단계: 핵심 텍스트 검증 통과.")

            # --- 2단계: 구조적 특징 검증 ---

            # 2-1. 라벨 존재 여부 확인
            label_found = any(page.search(label) for page in pdf.pages for label in REQUIRED_LABELS)
            if not label_found:
                #print(f"-> [판정 실패] 필수 라벨 '{REQUIRED_LABELS[0]}'을 찾을 수 없습니다.")
                return False
            #print("-> 2-1단계: 필수 라벨 검증 통과.")

            # 2-2. 테이블 구조 확인 (모든 페이지의 모든 테이블을 한 번에 가져옴)
            all_tables = [table for page in pdf.pages for table in page.find_tables()]
            if not all_tables:
                print("-> [판정 실패] 문서에서 테이블을 하나도 찾을 수 없습니다.")
                return False

            # 테이블 내 키워드와 헤더 존재 여부를 확인할 플래그
            keyword_in_table_found = False
            header_match_found = False

            for table in all_tables:
                # 테이블에서 텍스트 추출 시도 (비어있는 테이블 등 예외 처리)
                try:
                    extracted_table = table.extract(x_tolerance=3, y_tolerance=3)
                    if not extracted_table: continue
                except Exception:
                    continue

                # 학생 정보 테이블 키워드 확인
                first_cell_text = extracted_table[0][0]
                if first_cell_text and any(key in first_cell_text for key in REQUIRED_TABLE_KEYWORDS):
                    keyword_in_table_found = True

                # 학점 이수 현황 헤더 확인
                if extracted_header := extracted_table[0] == COURSE_HISTORY_HEADER:
                    header_match_found = True

            if not keyword_in_table_found:
                (f"-> [판정 실패] 테이블 내 필수 키워드 '{REQUIRED_TABLE_KEYWORDS[0]}'를 찾을 수 없습니다.")
                return False
            #print("-> 2-2단계: 테이블 내 키워드 검증 통과.")

            if not header_match_found:
                #print("-> [판정 실패] '학점이수현황' 테이블의 헤더 구조가 일치하지 않습니다.")
                return False
            #print("-> 2-3단계: 테이블 헤더 구조 검증 통과.")

    except Exception as e:
        # pdfplumber가 파일을 열지 못하는 경우 (손상, 암호화, PDF가 아닌 파일 등)
        #print(f"-> [판정 실패] 파일 처리 중 오류 발생: {e}")
        return False

    # 모든 검증을 통과한 경우
    #print("=> [최종 판정] 모든 검증 통과. 올바른 형식의 PDF입니다.")
    return True
