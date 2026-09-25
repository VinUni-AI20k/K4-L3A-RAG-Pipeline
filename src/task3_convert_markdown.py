"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

- legal/: PDF → Markdown bằng MarkItDown, metadata lấy từ landing/legal/sources.csv
  và frontmatter của file Markdown gốc (audience, category).
- news/: JSON crawl → Markdown, giữ url/title/date_crawled.

Mỗi file đầu ra có YAML frontmatter (doc_id, title, doc_type, url, ...) để Task 4
đọc lại metadata. Chạy lại sẽ ghi đè cùng tên file nên không tạo file trùng.
"""

import csv
import json
import re
import unicodedata
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

# Dòng giao diện của help.shopee.vn không mang nội dung chính sách.
BOILERPLATE_PATTERNS = [
    r"^.*\| Shopee Trung tâm trợ giúp\s*$",
    r"^Xin chào, Shopee có thể giúp gì cho bạn\?\s*$",
    r"^Nguồn: https?://\S+\s*$",
]


def write_markdown(output: Path, metadata: dict, title: str, body: str) -> None:
    """Ghi Markdown chuẩn hoá Unicode NFC (trang web có thể trả về dấu tổ hợp NFD)."""
    text = yaml_frontmatter(metadata) + f"# {title}\n\n{body}\n"
    output.write_text(unicodedata.normalize("NFC", text), encoding="utf-8")


def yaml_frontmatter(metadata: dict) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def remove_boilerplate(text: str) -> str:
    lines = [
        line for line in text.splitlines()
        if not any(re.match(pattern, line.strip()) for pattern in BOILERPLATE_PATTERNS)
    ]
    return "\n".join(lines)


def unwrap_pdf_text(text: str) -> str:
    """Nối các dòng bị ngắt do PDF layout thành đoạn văn, chuẩn hoá khoảng trắng."""
    paragraphs = []
    for block in re.split(r"\n\s*\n", text):
        joined = " ".join(line.strip() for line in block.splitlines() if line.strip())
        joined = re.sub(r"[ \t\xa0]+", " ", joined).strip()
        if joined:
            paragraphs.append(joined)
    return "\n\n".join(paragraphs)


def clean_web_markdown(text: str) -> str:
    """Bỏ ảnh, giữ chữ của link, bỏ query tracking và dòng trống thừa."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\*\*\s*\*\*", "", text)
    # Bảng HTML của help center bị crawl thành heading lẫn trong ô bảng:
    # bỏ dấu heading và các dòng chỉ gồm ký tự "|".
    text = re.sub(r"^\s*#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[\s|]*\|[\s|]*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[\s|:]*-{3,}[\s|:-]*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t\xa0]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_landing_frontmatter(path: Path) -> dict:
    from .task1_collect_legal_docs import split_frontmatter

    if not path.exists():
        return {}
    metadata, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    return metadata


def convert_legal_docs() -> None:
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    with (legal_dir / "sources.csv").open(encoding="utf-8") as file:
        sources = {row["doc_id"]: row for row in csv.DictReader(file)}

    converter = MarkItDown()
    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue
        row = sources.get(path.stem)
        if row is None:
            print(f"Skipped (not in sources.csv): {path.name}")
            continue
        extra = read_landing_frontmatter(legal_dir / f"{path.stem}.md")
        body = converter.convert(str(path)).text_content
        body = unwrap_pdf_text(remove_boilerplate(body))
        # Tiêu đề lặp lại (tiêu đề PDF + heading gốc) đã có trong H1 bên dưới.
        body = "\n\n".join(
            paragraph for paragraph in body.split("\n\n")
            if paragraph.casefold() != row["title"].casefold()
        )
        metadata = {
            "doc_id": row["doc_id"],
            "title": row["title"],
            "doc_type": "legal",
            "url": row["source_url"],
            "source_file": path.name,
            "retrieved_at": row["retrieved_at"],
            "document_version": row["document_version"],
            "audience": extra.get("audience", ""),
            "category": extra.get("category", ""),
        }
        output = output_dir / f"{path.stem}.md"
        write_markdown(output, metadata, row["title"], body)
        print(f"Converted: {path.name} → {output.relative_to(OUTPUT_DIR)}")


def convert_news_articles() -> None:
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(news_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        # Heading đầu tiên của bài chính là title; thay bằng H1 thống nhất.
        body = re.sub(r"^#{1,6}\s+.*\n", "", data["content_markdown"].lstrip(), count=1)
        body = clean_web_markdown(body)
        metadata = {
            "doc_id": path.stem,
            "title": data["title"],
            "doc_type": "news",
            "url": data["url"],
            "source_file": path.name,
            "date_crawled": data["date_crawled"],
        }
        output = output_dir / f"{path.stem}.md"
        write_markdown(output, metadata, data["title"], body)
        print(f"Converted: {path.name} → {output.relative_to(OUTPUT_DIR)}")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
