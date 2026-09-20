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


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải ít nhất 3 PDF/DOCX từ nguồn công khai."""
    # TODO: Có thể tải thủ công hoặc dùng requests.
    #
    # Ví dụ:
    # import requests
    #
    # sources = {
    #     "policy-a.pdf": "https://example.edu/policy-a.pdf",
    # }
    # for filename, url in sources.items():
    #     response = requests.get(url, timeout=30)
    #     response.raise_for_status()
    #     (DATA_DIR / filename).write_bytes(response.content)
    import requests

    sources = {
        "task-1-writing": "https://assets.ctfassets.net/unrdeg6se4ke/3eT3ue2RV5egjS34QqXdVt/ce0e178707e2021111f943ebbd9a0a8d/Writing-Band-descriptors-Task-1.pdf",
        "task-2-writing": "https://assets.ctfassets.net/unrdeg6se4ke/4AqjlJ7Tp1wLiY1j6DzpOg/39561e03e8d48ddc7648b479b903c701/Writing-Band-descriptors-Task-2.pdf",
        "sample-tests": "https://ielts.org/cdn/Sample-tests/ielts-academic-writing-sample-tasks-2023.pdf",
    }

    for filename, url in sources.items():
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        (DATA_DIR / filename).write_bytes(response.content)


if __name__ == "__main__":
    setup_directory()
    download_documents()
