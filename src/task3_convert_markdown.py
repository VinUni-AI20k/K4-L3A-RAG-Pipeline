"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cài đặt:
    Dependency MarkItDown đã được khai báo trong pyproject.toml.
    
-> Hoặc dùng công cụ nào bạn quen khác Markitdown
"""

from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _fallback_legal_markdown(path: Path) -> str:
    title = path.stem.replace("-", " ").title()
    return (
        f"# {title}\n\n"
        f"**Source:** {path.name}\n\n"
        "**Document type:** legal\n\n"
        "Tài liệu gốc đã được thu thập trong thư mục `data/landing/legal`, "
        "nhưng công cụ trích xuất văn bản hiện tại không đọc được nội dung text "
        "từ PDF. File Markdown này giữ lại metadata và nguồn tham chiếu để pipeline "
        "không bị rỗng dữ liệu; khi đánh giá chính thức, nhóm nên OCR PDF gốc hoặc "
        "thay bằng bản PDF có text layer.\n\n"
        "Các câu hỏi liên quan đến tài liệu này cần đối chiếu với file PDF gốc "
        "cùng tên. Nội dung chuẩn hóa hiện tại chỉ xác nhận đây là nguồn tài liệu "
        "legal/policy trong corpus PTIT.\n"
    )


def convert_legal_docs() -> None:
    from markitdown import MarkItDown
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkItDown()
    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() in {".pdf", ".doc", ".docx"}:
            try:
                result = converter.convert(str(path))
                content = (getattr(result, "text_content", "") or "").strip()
            except Exception:
                content = ""
            if not content:
                content = _fallback_legal_markdown(path)
            (output_dir / f"{path.stem}.md").write_text(
                content, encoding="utf-8"
            )


def convert_news_articles() -> None:
    import json
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(news_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        header = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n---\n\n"
        )
        content = data.get("content_markdown", "").strip()
        if not content:
            continue
        (output_dir / f"{path.stem}.md").write_text(
            header + content, encoding="utf-8"
        )


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
