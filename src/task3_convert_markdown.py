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

import json

from markitdown import MarkItDown


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _front_matter(*, title: str, source: str, doc_type: str, url: str | None) -> str:
    """Tạo metadata thống nhất để Task 4 có thể giữ nguyên provenance."""
    safe_title = title.replace('"', "'")
    safe_source = source.replace('"', "'")
    url_value = "null" if url is None else json.dumps(url, ensure_ascii=False)
    return (
        "---\n"
        f'title: "{safe_title}"\n'
        f'source: "{safe_source}"\n'
        f'doc_type: "{doc_type}"\n'
        f"url: {url_value}\n"
        "---\n\n"
    )


def convert_legal_docs() -> None:
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkItDown()

    for path in sorted(legal_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue
        text = converter.convert(str(path)).text_content.strip()
        if len(text) < 200:
            raise ValueError(f"Converted legal document is too short: {path.name}")
        output = output_dir / f"{path.stem}.md"
        output.write_text(
            _front_matter(
                title=path.stem.replace("_", " ").title(),
                source=path.name,
                doc_type="legal",
                url=None,
            )
            + f"# {path.stem.replace('_', ' ').title()}\n\n{text}\n",
            encoding="utf-8",
        )
        print(f"Saved: {output}")


def convert_news_articles() -> None:
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(news_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        required = {"url", "title", "date_crawled", "content_markdown"}
        if not required <= data.keys() or not all(str(data[key]).strip() for key in required):
            raise ValueError(f"Invalid news metadata: {path.name}")
        content = data["content_markdown"].strip()
        if len(content) < 200:
            raise ValueError(f"News article is too short: {path.name}")
        output = output_dir / f"{path.stem}.md"
        output.write_text(
            _front_matter(
                title=data["title"],
                source=path.name,
                doc_type="news",
                url=data["url"],
            )
            + f"# {data['title']}\n\n"
            + f"**Crawled:** {data['date_crawled']}\n\n"
            + content
            + "\n",
            encoding="utf-8",
        )
        print(f"Saved: {output}")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
