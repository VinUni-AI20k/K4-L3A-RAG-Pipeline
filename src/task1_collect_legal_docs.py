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


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Kiểm tra và thu thập các tài liệu IELTS chính sách / hướng dẫn trong data/landing/legal/."""
    setup_directory()
    
    expected_files = [
        "IELTS WRITING 1.pdf",
        "IELTS WRITING 2.pdf",
        "IELTS WRITING 3.pdf",
    ]

    valid_count = 0
    for filename in expected_files:
        target_path = DATA_DIR / filename
        if target_path.exists() and target_path.stat().st_size > 1024:
            size_mb = target_path.stat().st_size / (1024 * 1024)
            print(f"Verified: {filename} ({size_mb:.2f} MB)")
            valid_count += 1
        else:
            print(f"Missing or invalid file: {filename}")

    print(f"\nTổng số tài liệu hợp lệ: {valid_count}/{len(expected_files)}")
    if valid_count < 3:
        raise FileNotFoundError("Chưa đủ tối thiểu 3 tài liệu trong data/landing/legal/")


if __name__ == "__main__":
    download_documents()
