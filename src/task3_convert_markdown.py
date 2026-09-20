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

import json
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"
LEGAL_METADATA_PATH = LANDING_DIR / "legal" / "sources.json"


def load_legal_metadata() -> dict[str, dict[str, str]]:
    """Đọc manifest chứa title/source của tài liệu pháp lý."""
    if not LEGAL_METADATA_PATH.is_file():
        return {}
    data = json.loads(LEGAL_METADATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Metadata legal phải là JSON object: {LEGAL_METADATA_PATH}")
    return data


def convert_legal_docs() -> list[Path]:
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkItDown()
    metadata_by_file = load_legal_metadata()
    metadata_mtime = (
        LEGAL_METADATA_PATH.stat().st_mtime
        if LEGAL_METADATA_PATH.is_file()
        else 0
    )
    unreadable: list[Path] = []
    for path in legal_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".docx"}:
            continue
        destination = output_dir / path.relative_to(legal_dir).with_suffix(".md")
        source_mtime = max(path.stat().st_mtime, metadata_mtime)
        if destination.is_file() and destination.stat().st_mtime >= source_mtime:
            existing = destination.read_text(encoding="utf-8")
            if existing.startswith("---\n") and "\ndoc_type: legal\n" in existing:
                continue
        try:
            content = converter.convert(str(path)).text_content
        except Exception as error:
            print(f"Skipped unreadable document: {path.name} ({error})")
            unreadable.append(path)
            continue
        if not content or not content.strip():
            unreadable.append(path)
            continue
        metadata = metadata_by_file.get(path.name, {})
        title = metadata.get("title") or path.stem.replace("_", " ").strip().title()
        source = metadata.get("source") or path.name
        header = (
            "---\n"
            f"title: {json.dumps(title, ensure_ascii=False)}\n"
            f"source: {json.dumps(source, ensure_ascii=False)}\n"
            "doc_type: legal\n"
            "---\n\n"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(header + content.strip() + "\n", encoding="utf-8")
    return unreadable


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
    unreadable = convert_legal_docs()
    convert_news_articles()
    if unreadable:
        names = ", ".join(path.name for path in unreadable)
        raise RuntimeError(
            "Khong trich xuat duoc van ban tu tai lieu: "
            f"{names}. Hay OCR, Save As thanh DOCX chuan, hoac thay bang file co lop text."
        )
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
