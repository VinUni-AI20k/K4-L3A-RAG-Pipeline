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

Lưu ý: nhiều PDF ký số của chinhphu.vn là ảnh scan (không có lớp text) nên
convert_legal_docs() ưu tiên đọc bản .doc/.docx nếu có (xem SOURCES trong
task1_collect_legal_docs.py). File .doc (định dạng nhị phân cũ) được convert qua
LibreOffice — máy chạy task3 cần cài sẵn LibreOffice (lệnh `soffice` trong PATH):
    Ubuntu/Debian: sudo apt install libreoffice
    macOS:         brew install --cask libreoffice
"""

from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _convert_legacy_doc_to_text(path: Path) -> str:
    """Convert file .doc (binary cũ, MarkItDown không đọc được) bằng LibreOffice headless."""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run(
            [
                "soffice", "--headless", "--convert-to", "txt:Text",
                "--outdir", tmp_dir, str(path),
            ],
            check=True, capture_output=True, timeout=60,
        )
        txt_path = Path(tmp_dir) / f"{path.stem}.txt"
        return txt_path.read_text(encoding="utf-8") if txt_path.exists() else ""


def convert_legal_docs() -> None:
    """Convert PDF/DOCX vào standardized/legal.

    Nhiều bản PDF ký số của chinhphu.vn là ảnh scan (không có lớp text), nên với mỗi
    văn bản luật ưu tiên bản .docx/.doc (đánh máy lại, không lỗi OCR) nếu có; chỉ
    dùng .pdf khi văn bản đó không có bản .doc/.docx đi kèm.
    """
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkItDown()

    by_stem: dict[str, dict[str, Path]] = {}
    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue
        by_stem.setdefault(path.stem, {})[path.suffix.lower()] = path

    for stem, variants in sorted(by_stem.items()):
        source = variants.get(".docx") or variants.get(".doc") or variants[".pdf"]
        destination = output_dir / f"{stem}.md"

        if source.suffix.lower() == ".doc":
            content = _convert_legacy_doc_to_text(source).strip()
        else:
            content = converter.convert(str(source)).text_content.strip()

        if not content:
            print(f"Skip (empty conversion): {source.name}")
            continue
        destination.write_text(content, encoding="utf-8")
        print(f"Converted: {source.name} -> {destination.name}")


def convert_news_articles() -> None:
    """Convert JSON vào standardized/news."""
    import json

    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(news_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        body = (data.get("content_markdown") or "").strip()
        if not body:
            print(f"Skip (empty article): {path.name}")
            continue
        header = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n---\n\n"
        )
        destination = output_dir / f"{path.stem}.md"
        destination.write_text(header + body, encoding="utf-8")
        print(f"Converted: {path.name} -> {destination.name}")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
