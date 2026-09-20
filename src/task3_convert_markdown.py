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
from pypdf import PdfReader


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def extract_pdf_content(pdf_path: Path) -> str:
    """Trích xuất nội dung văn bản từ file PDF."""
    try:
        from markitdown import MarkItDown
        converter = MarkItDown()
        result = converter.convert(str(pdf_path))
        if result and result.text_content and len(result.text_content.strip()) > 100:
            return result.text_content.strip()
    except Exception:
        pass

    # Trích xuất chuẩn xác và ổn định qua pypdf
    reader = PdfReader(pdf_path)
    pages = []
    for idx, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        if text and text.strip():
            pages.append(text.strip())
    return "\n\n".join(pages)


def convert_legal_docs() -> None:
    """Convert tài liệu PDF/DOCX vào standardized/legal/ kèm metadata ở đầu file."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(legal_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in {".pdf", ".doc", ".docx"} and not path.name.startswith("."):
            print(f"Converting legal document: {path.name}...")
            content = extract_pdf_content(path)
            
            # Chuẩn hóa tên tiêu đề
            clean_title = path.stem.replace("-", " ").replace("_", " ").title()
            
            header = (
                f"# {clean_title}\n\n"
                f"**Source:** {path.name}\n\n"
                f"**Type:** Legal / Policy Document\n\n"
                f"---\n\n"
            )
            
            out_file = output_dir / f"{path.stem}.md"
            out_file.write_text(header + content, encoding="utf-8")
            print(f"Saved: {out_file} ({len(header + content)} chars)")


def convert_news_articles() -> None:
    """Convert JSON bài viết vào standardized/news/ kèm metadata ở đầu file."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(news_dir.glob("*.json")):
        print(f"Converting news article: {path.name}...")
        data = json.loads(path.read_text(encoding="utf-8"))
        
        content = data["content_markdown"].strip()
        lines = content.splitlines()
        if lines and lines[0].strip().lstrip("#").strip() == data["title"].strip():
            content = "\n".join(lines[1:]).lstrip()
        
        header = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n"
            f"---\n\n"
        )
        
        out_file = output_dir / f"{path.stem}.md"
        out_file.write_text(header + content, encoding="utf-8")
        print(f"Saved: {out_file} ({len(header + content)} chars)")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing sang standardized Markdown."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"\nAll documents standardized to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
