import os
import re
import zipfile
from io import BytesIO

##############################################
# 1. 스타일 수정 함수 (re.sub 분리)
##############################################
def fix_styles_content(content):
    """
    styles.xml 파일의 content에서 'applyNumberForm'을
    'applyNumberFormat'으로 변경한 결과를 반환한다.
    """
    return re.sub(r'applyNumberForm', 'applyNumberFormat', content)

##############################################
# 2. XLSX 파일의 스타일 수정 (메모리 내 처리)
##############################################
def fix_xlsx_file(input_path, output_path):
    """
    input_path에 있는 xlsx 파일을 읽어 메모리 내에서 압축 해제 후,
    xl/styles.xml 파일의 내용을 수정하고, 수정된 파일을 output_path에 저장한다.
    """
    # 입력 파일을 바이너리로 읽음
    with open(input_path, "rb") as f:
        xlsx_bytes = f.read()

    in_memory_zip = BytesIO(xlsx_bytes)
    new_zip_contents = {}

    # 기존 ZIP 파일을 읽으며, xl/styles.xml 파일이면 수정
    with zipfile.ZipFile(in_memory_zip, "r") as zip_in:
        for file_name in zip_in.namelist():
            content = zip_in.read(file_name)
            if file_name == "xl/styles.xml":
                content_str = content.decode("utf-8")
                fixed_str = fix_styles_content(content_str)
                content = fixed_str.encode("utf-8")
            new_zip_contents[file_name] = content

    # 메모리 내에 수정된 ZIP 파일 생성
    output_bytes = BytesIO()
    with zipfile.ZipFile(output_bytes, "w", zipfile.ZIP_DEFLATED) as zip_out:
        for file_name, content in new_zip_contents.items():
            zip_out.writestr(file_name, content)
    output_bytes.seek(0)

    # 결과를 output_path에 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(output_bytes.read())

##############################################
# 3. 지정한 루트 디렉토리 내의 모든 xlsx 파일을 재귀적으로 처리
#    오류 발생 시 에러 메시지를 error_report.txt에 기록
##############################################
def process_directory(input_root, output_root, error_report_path):
    error_lines = []
    total_files = 0

    for root, dirs, files in os.walk(input_root):
        for file in files:
            if file.lower().endswith(".xlsx"):
                total_files += 1
                input_file = os.path.join(root, file)
                # 입력 디렉토리 구조를 그대로 복원하여 출력 디렉토리 내에 저장
                rel_path = os.path.relpath(root, input_root)
                output_dir = os.path.join(output_root, rel_path)
                output_file = os.path.join(output_dir, file)
                try:
                    fix_xlsx_file(input_file, output_file)
                except Exception as e:
                    error_lines.append(
                        f"파일: {input_file}\n오류: {str(e)}\n{'-'*40}\n"
                    )

    if error_lines:
        with open(error_report_path, "w", encoding="utf-8") as f:
            f.writelines(error_lines)
        print(f"총 {total_files}개의 파일 중 일부에서 오류가 발생했습니다. 오류 리포트: {error_report_path}")
    else:
        print(f"총 {total_files}개의 파일의 스타일 수정을 성공적으로 완료하였습니다.")

##############################################
# 4. 메인 함수
##############################################
def main():
    # 원본 xlsx 파일들이 있는 루트 디렉토리 (예: downloads)
    input_root = "target"
    # 수정된 파일들을 저장할 출력 디렉토리 (예: fixed)
    output_root = "target_fixed"
    # 오류 리포트 파일 (출력 디렉토리 하위에 생성)
    error_report_path = os.path.join(output_root, "error_report.txt")

    process_directory(input_root, output_root, error_report_path)

if __name__ == "__main__":
    main()
