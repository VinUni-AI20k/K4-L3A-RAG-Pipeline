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


def download_documents(sources: dict[str, str] | None = None) -> None:
    """Tải từ mapping tên file → URL, hoặc kiểm tra tài liệu tải thủ công."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sources = sources or {}
    for filename, url in sources.items():
        if (
            not filename.isascii()
            or "/" in filename
            or "\\" in filename
            or ":" in filename
            or Path(filename).suffix.lower() not in {".pdf", ".docx"}
        ):
            raise ValueError(f"Tên file phải không dấu và có đuôi PDF/DOCX: {filename}")
        if not url.startswith(("https://", "http://")):
            raise ValueError(f"URL phải dùng HTTP hoặc HTTPS: {url}")

    if sources:
        with requests.Session() as session:
            for filename, url in sources.items():
                with session.get(url, timeout=30) as response:
                    response.raise_for_status()
                    content = response.content
                    if not content:
                        raise ValueError(f"Tài liệu tải về rỗng: {url}")
                    (DATA_DIR / filename).write_bytes(content)
                print(f"Saved: {DATA_DIR / filename}")

    documents = [
        path for path in DATA_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".pdf", ".docx"}
        and path.stat().st_size > 0
    ]
    if len(documents) < 3:
        raise ValueError(
            f"Cần ít nhất 3 tài liệu PDF/DOCX; hiện có {len(documents)}. "
            f"Tải thủ công vào {DATA_DIR} hoặc truyền sources={{tên_file: URL}} "
            "cho download_documents()."
        )
    print(f"Ready: {len(documents)} documents in {DATA_DIR}")


if __name__ == "__main__":
    setup_directory()
    download_documents()
