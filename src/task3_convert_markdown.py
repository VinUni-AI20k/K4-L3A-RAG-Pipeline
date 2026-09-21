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
    """Convert PDF/DOCX từ data/landing/legal/ sang data/standardized/legal/*.md."""
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkItDown()

    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() in {".pdf", ".doc", ".docx"}:
            output_file = output_dir / f"{path.stem}.md"
            if output_file.exists() and len(output_file.read_text(encoding="utf-8").strip()) >= 200:
                print(f"Skipped (already standardized): {output_file.name}")
                continue

            print(f"Converting PDF: {path.name} ...")
            result = converter.convert(str(path))
            content = result.text_content.strip()

            if len(content) < 200:
                raise ValueError(f"Extracted content too short for {path.name}: {len(content)} chars")

            output_file.write_text(content, encoding="utf-8")
            print(f"Saved legal markdown: {output_file} ({len(content)} chars)")


def convert_news_articles() -> None:
    """Convert JSON từ data/landing/news/ sang data/standardized/news/*.md."""
    import json

    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(news_dir.glob("*.json")):
        output_file = output_dir / f"{path.stem}.md"
        data = json.loads(path.read_text(encoding="utf-8"))

        header = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n---\n\n"
        )
        full_content = (header + data["content_markdown"]).strip()
        if len(full_content) < 200:
            raise ValueError(f"Standardized article too short for {path.name}: {len(full_content)} chars")

        output_file.write_text(full_content, encoding="utf-8")
        print(f"Saved news markdown: {output_file} ({len(full_content)} chars)")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
