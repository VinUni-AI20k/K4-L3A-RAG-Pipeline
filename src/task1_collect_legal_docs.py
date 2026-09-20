"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Hướng dẫn:
    1. Chọn chủ đề của nhóm.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Ví dụ tài liệu: học phí, học bổng, ký túc xá, quy trình đăng ký.
Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

from pathlib import Path

import requests


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

# Nguồn chính thức của UEH. Các văn bản này cùng thuộc chủ đề chính sách
# sinh viên, giúp corpus nhất quán cho retrieval và evaluation.
DOCUMENT_SOURCES = {
    "quy_che_dao_tao_dai_hoc.pdf": (
        "https://daotao.ueh.edu.vn/Content/media/files/"
        "QuyChe_QuyDinh/DHCQ/ThongTu08.pdf"
    ),
    "quy_dinh_hoc_bong.pdf": (
        "https://daotao.ueh.edu.vn/Content/media/files/"
        "QuyChe_QuyDinh/DHCQ/2024.08/QD2976_HocBong.pdf"
    ),
    "quy_dinh_cong_tac_sinh_vien.pdf": (
        "https://ueh.edu.vn/userfiles/file/File_KinhTe/"
        "090226_Quy_dinh_cong_tac_sinh_vien.pdf"
    ),
}


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải ít nhất 3 PDF/DOCX từ nguồn công khai."""
    setup_directory()
    headers = {"User-Agent": "K4-RAG-Lab/1.0 (educational project)"}

    for filename, url in DOCUMENT_SOURCES.items():
        output = DATA_DIR / filename
        if output.exists() and output.stat().st_size > 1024:
            print(f"Exists: {output}")
            continue

        response = requests.get(url, headers=headers, timeout=45)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "html" in content_type or len(response.content) <= 1024:
            raise ValueError(f"Invalid document response from {url}")
        output.write_bytes(response.content)
        print(f"Saved: {output}")


if __name__ == "__main__":
    setup_directory()
    download_documents()
