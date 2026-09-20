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
    """Convert PDF/DOCX vào standardized/legal."""
    import fitz

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    titles = {
        "quy_che_dao_tao_dhqghn_3626": "Quy chế đào tạo đại học tại Đại học Quốc gia Hà Nội (QĐ 3626/QĐ-ĐHQGHN)",
        "quy_dinh_hoc_bong_dhqghn_4618": "Quy định về công tác quản lý và sử dụng học bổng tại Đại học Quốc gia Hà Nội (QĐ 4618/QĐ-ĐHQGHN)",
        "quy_trinh_canh_bao_hoc_vu_dhqghn": "Quy trình xét cảnh báo học vụ cho sinh viên chính quy tại ĐHQGHN (QĐ 2244)",
    }

    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() in {".pdf", ".doc", ".docx"} and not path.name.startswith("."):
            title = titles.get(path.stem, path.stem.replace("_", " ").title())
            
            # Thử dùng MarkItDown nếu có
            text_content = ""
            try:
                from markitdown import MarkItDown
                converter = MarkItDown()
                res = converter.convert(str(path))
                if res and res.text_content and len(res.text_content.strip()) >= 200:
                    text_content = res.text_content.strip()
            except Exception:
                text_content = ""

            # Resilient fallback: Dùng PyMuPDF (fitz)
            if not text_content:
                doc = fitz.open(str(path))
                pages = []
                for i, page in enumerate(doc, 1):
                    page_text = page.get_text() or ""
                    if page_text.strip():
                        pages.append(f"<!-- Trang {i} -->\n\n{page_text.strip()}")
                text_content = "\n\n".join(pages)

            header = (
                f"# {title}\n\n"
                f"**Source:** {path.name}\n\n"
                f"**Doc Type:** legal\n\n"
                f"---\n\n"
            )
            output_file = output_dir / f"{path.stem}.md"
            output_file.write_text(header + text_content, encoding="utf-8")
            print(f"Converted legal: {output_file.name} ({len(header + text_content):,} characters)")


def convert_news_articles() -> None:
    """Convert JSON vào standardized/news."""
    import json

    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(news_dir.glob("*.json")):
        if path.name.startswith("."):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        header = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n"
            f"**Doc Type:** news\n\n"
            f"---\n\n"
        )
        content = data.get("content_markdown", "")
        output_file = output_dir / f"{path.stem}.md"
        output_file.write_text(header + content, encoding="utf-8")
        print(f"Converted news: {output_file.name} ({len(header + content):,} characters)")



def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
