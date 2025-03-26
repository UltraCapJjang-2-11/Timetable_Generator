# home/services/pdf_service.py
import pdfplumber

def pdf_to_text(pdf_path: str) -> str:
    """
    pdfplumber를 이용해 PDF를 텍스트로 변환.
    PDF가 스캔 이미지라면 OCR 필요.
    """
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                texts.append(page_text)
    return "\n".join(texts)
