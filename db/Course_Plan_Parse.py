import os
import glob
import json
import pandas as pd

############################
# 기존 유틸 함수들 그대로 유지
############################
def find_in_column(df, label, label_col=0):
    """
    df의 label_col 열(A열 등)을 위에서부터 스캔하여,
    주어진 label과 정확히 일치하는 셀이 있다면 해당 행(row 인덱스)을 반환.
    없다면 None을 반환.
    """
    for row_index in range(len(df)):
        cell_val = str(df.iloc[row_index, label_col]).strip()
        if cell_val == label:  # 완전 일치 조건
            return row_index
    return None

def read_multiline_data(df, label, label_col=0, data_col=3):
    """
    1) label_col 열에서 `label` 문자열과 정확히 일치하는 행(row_index)을 찾는다.
    2) 해당 행의 data_col 열(D열 등)을 읽고,
    3) 이후 행을 계속 내려가며 label_col이 비어 있으면(data_col에만 내용이 있다면)
       앞서 찾은 라벨의 연속된 내용으로 간주해 이어붙인다.
    4) 새 라벨(즉, label_col에 무언가 텍스트가 있는)이 등장하면 중단한다.

    최종적으로 여러 줄을 '\n'로 합쳐 하나의 문자열로 반환한다.
    찾지 못하면 None을 반환한다.
    """
    # 먼저 label에 해당하는 행 찾기
    row_idx = find_in_column(df, label, label_col)
    if row_idx is None:
        return None  # 해당 라벨이 없다면 None 반환

    # 첫 번째 줄은 라벨이 있는 행의 data_col 내용
    base_text = [str(df.iloc[row_idx, data_col]).strip()]

    # 이후 행을 하나씩 내려가며, label_col(A열 등)이 비어 있는지 검사
    next_r = row_idx + 1
    while next_r < len(df):
        val_label_col = str(df.iloc[next_r, label_col]).strip()
        # 만약 A열 등에 무언가 라벨(텍스트)이 새로 등장하면 → 중단
        if val_label_col != "nan" and val_label_col:
            break

        # A열이 "nan"이거나 공백이라면 → 이전 라벨의 연속된 내용
        val_data_col = str(df.iloc[next_r, data_col]).strip()
        if val_data_col:
            base_text.append(val_data_col)

        next_r += 1

    # 여러 줄을 개행 문자로 합쳐 반환
    return "\n".join(base_text)

############################
# 핵심 파싱 로직을 함수로 분리
############################
def parse_xlsx(file_path):
    """
    주어진 xlsx 파일을 읽어,
    - 교과목 정보(data)
    - 교과목 개요(data_overview)
    - 주별 강의계획(weekly_plan)
    세 가지를 딕셔너리 형태로 반환한다.
    """

    # 1) 엑셀 읽기 (header=None: 모든 행을 0-based로 읽음)
    df = pd.read_excel(file_path, header=None, engine="openpyxl")

    ########################################
    # 1. 교과목 정보 추출 (data)
    ########################################
    data = {}

    # (1) "개설연도-학기" 라벨 → 같은 행의 E열(4), H열(7)을 각자 "개설연도", "학기"로
    row_idx = find_in_column(df, "개설연도-학기", label_col=0)
    if row_idx is not None:
        data["개설연도"] = df.iloc[row_idx, 4]
        data["학기"]     = df.iloc[row_idx, 7]

    # (2) "개설학과" 라벨 → 같은 행의 R열(17)
    row_idx = find_in_column(df, "개설학과", label_col=11)
    if row_idx is not None:
        data["개설학과"] = df.iloc[row_idx, 17]

    # (3) "교과목번호-분반번호"
    row_idx = find_in_column(df, "교과목번호-분반번호", label_col=0)
    if row_idx is not None:
        data["교과목번호"] = df.iloc[row_idx, 4]
        data["분반번호"]   = df.iloc[row_idx, 7]

    # (4) "교과목명" 라벨 → R열(17)
    row_idx = find_in_column(df, "교과목명", label_col=11)
    if row_idx is not None:
        data["교과목명"] = df.iloc[row_idx, 17]

    # (5) "이수구분" 라벨 → E열(4)
    row_idx = find_in_column(df, "이수구분", label_col=0)
    if row_idx is not None:
        data["이수구분"] = df.iloc[row_idx, 4]

    # (6) "학점/시수" 라벨 → R열(17)
    row_idx = find_in_column(df, "학점/시수", label_col=11)
    if row_idx is not None:
        data["학점/시수"] = df.iloc[row_idx, 17]

    # (7) "강의시간/강의실" 라벨 → E열(4)
    row_idx = find_in_column(df, "강의시간/강의실", label_col=0)
    if row_idx is not None:
        data["강의시간/강의실"] = df.iloc[row_idx, 4]

    # (8) "수업방식" 라벨 → E열(4)
    row_idx = find_in_column(df, "수업방식", label_col=0)
    if row_idx is not None:
        data["수업방식"] = df.iloc[row_idx, 4]

    # (9) "강의언어" 라벨 → E열(4)
    row_idx = find_in_column(df, "강의언어", label_col=0)
    if row_idx is not None:
        data["강의언어"] = df.iloc[row_idx, 4]

    # (10) "담당교수" 라벨 → R열(17)
    row_idx = find_in_column(df, "담당교수", label_col=11)
    if row_idx is not None:
        data["담당교수"] = df.iloc[row_idx, 17]

    # (11) "전화" 라벨 → E열(4)
    row_idx = find_in_column(df, "전화", label_col=0)
    if row_idx is not None:
        data["전화"] = df.iloc[row_idx, 4]

    # (12) "이메일" 라벨 → R열(17)
    row_idx = find_in_column(df, "E-mail", label_col=11)
    if row_idx is not None:
        data["이메일"] = df.iloc[row_idx, 17]

    # (13) "강의정원" 라벨 → E열(4)
    row_idx = find_in_column(df, "강의정원", label_col=0)
    if row_idx is not None:
        data["강의정원"] = df.iloc[row_idx, 4]

    # (14) "학과전화" 라벨 → R열(17)
    row_idx = find_in_column(df, "학과전화", label_col=11)
    if row_idx is not None:
        data["학과전화"] = df.iloc[row_idx, 17]

    # (15) "선수과목" 라벨 → E열(4)
    row_idx = find_in_column(df, "선수과목", label_col=0)
    if row_idx is not None:
        data["선수과목"] = df.iloc[row_idx, 4]

    # (16) "수강대상" 라벨 → R열(17)
    row_idx = find_in_column(df, "수강대상", label_col=11)
    if row_idx is not None:
        data["수강대상"] = df.iloc[row_idx, 17]

    # (17) "강의 맛보기" 라벨 → E열(4)
    row_idx = find_in_column(df, "강의 맛보기", label_col=0)
    if row_idx is not None:
        data["강의맛보기"] = df.iloc[row_idx, 4]

    ########################################
    # 2. 교과목 개요 추출 (data_overview)
    ########################################
    data_overview = {
        "강의개요":       read_multiline_data(df, "강의개요", label_col=0, data_col=3),
        "학습목표":       read_multiline_data(df, "학습목표", label_col=0, data_col=3),
        "문제해결방법":    read_multiline_data(df, "문제해결방법", label_col=0, data_col=3)
    }

    # (4) "수업진행방법"
    row_idx = find_in_column(df, "수업진행방법", label_col=0)
    if row_idx is not None:
        data_overview["수업진행방법"] = {
            "강의":      df.iloc[row_idx + 1, 3],
            "토의/토론":  df.iloc[row_idx + 1, 6],
            "실험/실습":  df.iloc[row_idx + 1, 9],
            "현장학습":   df.iloc[row_idx + 1, 13],
            "개별/팀별 발표": df.iloc[row_idx + 1, 18],
            "기타":      df.iloc[row_idx + 1, 22],
        }
        data_overview["수업진행방법"]["상세정보"] = df.iloc[row_idx + 2, 6]

    # (5) "평가방법"
    row_idx = find_in_column(df, "평가방법", label_col=0)
    if row_idx is not None:
        data_overview["평가방법"] = {
            "중간고사": df.iloc[row_idx + 1, 3],
            "기말고사": df.iloc[row_idx + 1, 6],
            "출석":    df.iloc[row_idx + 1, 9],
            "퀴즈":    df.iloc[row_idx + 1, 13],
            "과제":    df.iloc[row_idx + 1, 18],
            "기타":    df.iloc[row_idx + 1, 22],
        }
        data_overview["평가방법"]["상세정보"] = df.iloc[row_idx + 2, 6]

    # (6) "프로그램 학습성과의 평가"
    row_idx = find_in_column(df, "프로그램 학습성과의 평가", label_col=0)
    if row_idx is not None:
        data_overview["프로그램 학습성과의 평가"] = df.iloc[row_idx, 3]

    # (7) "교재 및 참고문헌"
    row_idx = find_in_column(df, "교재 및 참고문헌", label_col=0)
    if row_idx is not None:
        data_overview["교재 및 참고 문헌"] = df.iloc[row_idx, 3]

    # (8) "핵심역량과\n연계성"
    row_idx = find_in_column(df, "핵심역량과\n연계성", label_col=0)
    if row_idx is not None:
        data_overview["핵심역량과 연계성"] = df.iloc[row_idx, 3]

    ########################################
    # C. 주별 강의계획 (weekly_plan)
    ########################################
    weekly_plan = []
    for r in range(df.shape[0]):
        row_a = str(df.iloc[r, 0]).strip()
        if not row_a.isdigit():
            continue

        week_number = int(row_a)
        lecture_content = str(df.iloc[r, 1]).strip()

        assignment_scope = ""
        if df.shape[1] > 15:
            assignment_scope = str(df.iloc[r, 15]).strip()

        remarks = ""
        if df.shape[1] > 21:
            remarks = str(df.iloc[r, 21]).strip()

        weekly_plan.append({
            "주차": week_number,
            "수업내용": lecture_content,
            "교재범위및과제물": assignment_scope,
            "비고": remarks
        })


    ########################################
    # 파싱 결과를 하나의 딕셔너리로 합쳐 반환
    ########################################
    return {
        "교과목정보": data,
        "교과목개요": data_overview,
        "주별강의계획": weekly_plan
    }

############################
# 메인: 폴더 내 모든 XLSX → JSON 변환
############################
def main():
    # 1) result 디렉토리 생성 (없으면 생성)
    os.makedirs("result", exist_ok=True)

    # 2) ../target/ 폴더 내의 모든 xlsx 파일 찾기
    xlsx_files = glob.glob("../target/*.xlsx")

    for xlsx_path in xlsx_files:
        print(f"[INFO] 파일 처리 중: {xlsx_path}")

        # (a) 파싱
        result_dict = parse_xlsx(xlsx_path)

        # (b) JSON 파일명 만들기 (ex: "result/1.json")
        #     xlsx_path에서 파일명만 추출 후 확장자만 .json으로 변경
        base_name = os.path.basename(xlsx_path)            # "1.xlsx"
        json_name = os.path.splitext(base_name)[0] + ".json"  # "1.json"
        json_path = os.path.join("result", json_name)

        # (c) JSON으로 저장 (ensure_ascii=False로 하면 한글이 그대로 저장됨)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)

        print(f" → JSON 파일 생성 완료: {json_path}")

if __name__ == "__main__":
    main()
