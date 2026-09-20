"""
Task 1 — Kiểm tra tài liệu PDF đã thu thập thủ công.

Hướng dẫn:
    1. Chọn chủ đề của nhóm.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Ví dụ tài liệu: học phí, học bổng, ký túc xá, quy trình đăng ký.
Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Xác nhận ít nhất ba tài liệu đã được đặt vào thư mục landing."""
    documents = sorted(
        path for path in DATA_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in {".pdf", ".doc", ".docx"}
    )
    if len(documents) < 3:
        raise ValueError(f"Cần ít nhất 3 PDF/DOCX trong {DATA_DIR}; hiện có {len(documents)}")

    for path in documents:
        if path.stat().st_size <= 1024:
            raise ValueError(f"Tài liệu quá nhỏ hoặc rỗng: {path}")
        if path.suffix.lower() == ".pdf":
            with path.open("rb") as stream:
                if stream.read(5) != b"%PDF-":
                    raise ValueError(f"File không có định dạng PDF hợp lệ: {path}")
        print(f"Found: {path.name} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    setup_directory()
    download_documents()
