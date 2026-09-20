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


def convert_legal_docs() -> None:
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkItDown()
    for path in legal_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".docx"}:
            continue
        destination = output_dir / path.relative_to(legal_dir).with_suffix(".md")
        if destination.is_file() and destination.stat().st_mtime >= path.stat().st_mtime:
            if destination.stat().st_size > 0:
                continue
        content = converter.convert(str(path)).text_content
        if not content or not content.strip():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")


def convert_news_articles() -> None:
    import json

    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in news_dir.rglob("*.json"):
        if not path.is_file():
            continue
        destination = output_dir / path.relative_to(news_dir).with_suffix(".md")
        if destination.is_file():
            destination_stat = destination.stat()
            if destination_stat.st_size > 0 and destination_stat.st_mtime >= path.stat().st_mtime:
                continue
        data = json.loads(path.read_text(encoding="utf-8"))
        content = data["content_markdown"]
        if not content or not content.strip():
            continue
        header = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n---\n\n"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(header + content, encoding="utf-8")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
