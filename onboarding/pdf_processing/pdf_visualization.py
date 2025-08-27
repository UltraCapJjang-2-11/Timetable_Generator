# --- 필요한 라이브러리 임포트 ---
import os
from typing import Dict, Any, List
import pdfplumber  # PDF의 텍스트, 테이블, 좌표 등 구조적 정보를 다루는 라이브러리
from PIL import Image, ImageDraw  # 파이썬 이미지 처리 표준 라이브러리 (이미지 생성, 드로잉 담당)
import fitz  # PyMuPDF 라이브러리. PDF를 고품질 이미지로 렌더링(변환)하는 데 사용


# 시각화 그룹 정의:
# 각 딕셔너리는 하나의 PNG 파일을 생성하기 위한 규칙입니다.
# - output_filename: 생성될 PNG 파일의 이름
# - group_name: 처리 과정을 알려주는 로그용 그룹 이름
# - keys: 이 그룹에 포함시킬 테이블들의 이름 (identify_document_objects가 반환하는 딕셔너리의 키)
# - color: 테두리 상자의 색상 (R, G, B)
# - highlight_color: 텍스트 배경 하이라이트 색상 (R, G, B, Alpha(투명도))
VISUALIZATION_GROUPS = [
    {
        "key_name": "student_info",  # -- 반환 딕셔너리의 키로 사용될 이름
        "output_filename": "report_visualization_student_info.png",
        "group_name": "학생 정보",
        "keys": ['학생정보_소속대학', '학생정보_개인정보0', '학생정보_개인정보1', '학생정보_개인정보2', '학생정보_개인정보3'],
        "color": (30, 144, 255), "highlight_color": (30, 144, 255, 50)
    },
    {
        "key_name": "credit_summary", # -- 반환 딕셔너리의 키로 사용될 이름
        "output_filename": "report_visualization_credit_summary.png",
        "group_name": "학점 요약",
        "keys": ['이수구분별 취득학점 상세 합계표', '이수구분별 취득학점 합계표'],
        "color": (220, 20, 60), "highlight_color": (220, 20, 60, 50)
    },
    {
        "key_name": "course_history", # -- 반환 딕셔너리의 키로 사용될 이름
        "output_filename": "report_visualization_course_history.png",
        "group_name": "학점 이수 현황",
        "keys": ['학점이수현황', '성적정보'],
        "color": (50, 205, 50), "highlight_color": (50, 205, 50, 50)
    }
]



def generate_visual_reports(file_path: str, identified_objects: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
    """
    주어진 PDF 파일과 식별된 객체들을 사용하여 시각화 리포트를 생성하고,
    생성된 파일들의 경로를 담은 딕셔너리를 반환합니다.

    :param file_path: 처리할 원본 PDF 파일의 전체 경로
    :param identified_objects: extract_to_dict.py가 식별한 객체 딕셔너리
    :param output_dir: 생성될 모든 PNG 파일이 저장될 디렉토리의 전체 경로
    :return: 생성된 파일들의 경로를 담은 딕셔너리
    """
    # -- 1. 반환할 결과를 담을 딕셔너리 초기화
    generated_files = {
        "original_pages": [],
    }

    # -- 2. 하드코딩된 출력 디렉토리 대신, 파라미터로 받은 output_dir 사용
    os.makedirs(output_dir, exist_ok=True)

    saved_original_pages = set()
    pdf_fitz = fitz.open(file_path)

    with pdfplumber.open(file_path) as pdf_plumber:
        for group in VISUALIZATION_GROUPS:
            pages_to_process: Dict[int, List[Any]] = {}
            for key in group['keys']:
                if key in identified_objects:
                    items = identified_objects[key] if isinstance(identified_objects[key], list) else [
                        identified_objects[key]]
                    for item in items:
                        if isinstance(item, pdfplumber.table.Table):
                            pages_to_process.setdefault(item.page.page_number, []).append(item)

            if not pages_to_process:
                continue

            processed_images = []
            for page_num in sorted(pages_to_process.keys()):
                p_page = pdf_plumber.pages[page_num - 1]
                page_fitz = pdf_fitz.load_page(page_num - 1)
                pix = page_fitz.get_pixmap(dpi=300)
                pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                if page_num not in saved_original_pages:
                    original_filename = f"original_page_{page_num}.png"
                    # -- 3. 하드코딩된 경로 대신, 파라미터로 받은 output_dir 사용
                    original_output_path = os.path.join(output_dir, original_filename)
                    pil_image.save(original_output_path, 'PNG')
                    # -- 4. 반환할 딕셔너리에 원본 페이지 경로 추가
                    generated_files["original_pages"].append(original_output_path)
                    saved_original_pages.add(page_num)

                scaling_factor = pil_image.width / p_page.width
                draw = ImageDraw.Draw(pil_image, "RGBA")

                tables_on_page = pages_to_process[page_num]
                for table in tables_on_page:
                    bbox = table.bbox
                    scaled_bbox = tuple(coord * scaling_factor for coord in bbox)
                    chars_in_bbox = p_page.crop(bbox).chars
                    for char in chars_in_bbox:
                        scaled_char_bbox = (
                            char['x0'] * scaling_factor, char['top'] * scaling_factor,
                            char['x1'] * scaling_factor, char['bottom'] * scaling_factor
                        )
                        draw.rectangle(scaled_char_bbox, fill=group['highlight_color'])
                    draw.rectangle(scaled_bbox, outline=group['color'], width=7)

                processed_images.append(pil_image)

            # -- 5. 하드코딩된 경로 대신, 파라미터로 받은 output_dir 사용
            output_path = os.path.join(output_dir, group['output_filename'])

            if len(processed_images) == 1:
                processed_images[0].save(output_path, 'PNG')
            elif len(processed_images) > 1:
                max_width = max(img.width for img in processed_images)
                total_height = sum(img.height for img in processed_images)
                composite_image = Image.new('RGB', (max_width, total_height), 'white')
                current_y = 0
                for img in processed_images:
                    composite_image.paste(img, (0, current_y))
                    current_y += img.height
                composite_image.save(output_path, 'PNG')

            # -- 6. 반환할 딕셔너리에 시각화 리포트 경로 추가
            generated_files[group['key_name']] = output_path

    pdf_fitz.close()

    # -- 7. 최종 결과 딕셔너리 반환
    return generated_files


