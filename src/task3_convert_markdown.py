"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown (chủ đề: Du lịch).

1. Dùng MarkItDown để convert PDF/DOCX nếu đã cài; nếu chưa cài, đọc thẳng
   nút văn bản trong .docx (OpenXML) làm fallback.
2. Đọc JSON tin và giữ metadata ở đầu file Markdown.
3. Giữ cấu trúc thư mục legal/ và news/.
4. Không tạo file rỗng hoặc file trùng khi chạy lại.
"""

import json
import re
import zipfile
from pathlib import Path

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _extract_docx_text(path: Path) -> str:
    """Fallback đọc nội dung text của .docx không cần thư viện ngoài."""
    with zipfile.ZipFile(path) as archive:
        document = archive.read("word/document.xml").decode("utf-8")
    paragraphs = re.findall(r"<w:p[ >].*?</w:p>", document, flags=re.S)
    parts = []
    for paragraph in paragraphs:
        text = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", paragraph, flags=re.S))
        if text.strip():
            parts.append(text)
    return "\n\n".join(parts)


def convert_legal_docs() -> None:
    """Convert PDF/DOCX trong landing/legal sang standardized/legal."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from markitdown import MarkItDown  # noqa: PLC0415 - dep optional

        converter = MarkItDown()
    except ImportError:
        converter = None

    for path in sorted(legal_dir.iterdir()):
        if path.name.startswith("~$"):
            continue
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue
        output = output_dir / f"{path.stem}.md"
        if output.exists() and output.stat().st_size > 0:
            print(f"Skipped (already converted): {output}")
            continue

        try:
            if converter is not None:
                text = converter.convert(str(path)).text_content
            elif path.suffix.lower() == ".docx":
                text = _extract_docx_text(path)
            else:
                print(f"Skipped (cần markitdown để đọc {path.name})")
                continue
            text = text.strip()
            if not text:
                raise RuntimeError("nội dung rỗng sau khi convert")
            output.write_text(text, encoding="utf-8")
            print(f"Converted: {output} ({len(text)} ký tự)")
        except Exception as error:  # noqa: BLE001 - báo lỗi rõ cho từng file
            print(f"Failed: {path.name} — {error}")


def convert_news_articles() -> None:
    """Convert JSON tin trong landing/news sang standardized/news."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(news_dir.glob("*.json")):
        output = output_dir / f"{path.stem}.md"
        if output.exists() and output.stat().st_size > 0:
            print(f"Skipped (already converted): {output}")
            continue

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            header = (
                f"# {data['title']}\n\n"
                f"**Source:** {data['url']}\n\n"
                f"**Crawled:** {data['date_crawled']}\n\n---\n\n"
            )
            output.write_text(header + data["content_markdown"], encoding="utf-8")
            print(f"Converted: {output}")
        except Exception as error:  # noqa: BLE001 - báo lỗi rõ cho từng file
            print(f"Failed: {path.name} — {error}")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()