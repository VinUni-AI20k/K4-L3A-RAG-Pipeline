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
import re
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _clean_content(text: str) -> str:
    """Làm sạch nội dung: chuẩn hóa dòng trắng thừa và ký tự rác."""
    # Loại bỏ khoảng trắng thừa ở cuối mỗi dòng
    lines = [line.rstrip() for line in text.splitlines()]
    # Giới hạn số dòng trắng liên tiếp tối đa là 1
    cleaned_lines = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                cleaned_lines.append("")
                prev_blank = True
        else:
            cleaned_lines.append(line)
            prev_blank = False
    return "\n".join(cleaned_lines).strip()


def convert_legal_docs() -> None:
    """Đọc tài liệu pháp lý từ landing/legal và chuẩn hóa sang standardized/legal.
    
    Hỗ trợ cả .md, .docx, .doc, .pdf và loại trừ trùng lặp theo stem.
    """
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Thu thập tất cả các file hợp lệ, nhóm theo stem để tránh trùng lặp
    files_by_stem: dict[str, Path] = {}
    # Ưu tiên .md hoặc .docx
    for path in sorted(legal_dir.iterdir()):
        if path.is_file() and not path.name.startswith(".") and path.suffix.lower() in {".md", ".docx", ".doc", ".pdf"}:
            stem = path.stem
            # Nếu chưa có hoặc nếu file hiện tại là .md (chứa text gốc), lưu lại
            if stem not in files_by_stem or path.suffix.lower() == ".md":
                files_by_stem[stem] = path

    legal_meta = {
        "chinh-sach-bao-ve-du-lieu-ca-nhan": {
            "title": "Chính sách bảo vệ dữ liệu cá nhân của Công ty Cổ phần Vinhomes",
            "source": "https://vinhomes.vn",
            "date": "01/07/2023",
        },
        "quy-dinh-xu-ly-khieu-nai": {
            "title": "Quy định xử lý khiếu nại yêu cầu của khách hàng",
            "source": "https://vinhomes.vn",
            "date": "05/05/2025",
        },
        "quy-tac-bao-ve-thong-tin": {
            "title": "Quy tắc bảo vệ thông tin người tiêu dùng của Công ty Cổ phần Vinhomes",
            "source": "https://vinhomes.vn",
            "date": "01/07/2024",
        },
    }

    for stem, path in files_by_stem.items():
        content = ""
        if path.suffix.lower() == ".md":
            content = path.read_text(encoding="utf-8")
        elif path.suffix.lower() in {".pdf", ".doc", ".docx"}:
            try:
                from markitdown import MarkItDown
                converter = MarkItDown()
                result = converter.convert(str(path))
                content = result.text_content
            except Exception:
                try:
                    import docx
                    doc = docx.Document(str(path))
                    content = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
                except Exception:
                    content = path.read_text(encoding="utf-8", errors="ignore")

        if not content.strip():
            continue

        meta = legal_meta.get(stem, {})
        title = meta.get("title")
        if not title:
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            title = lines[0].lstrip("#").strip() if lines else stem.replace("-", " ").title()

        source = meta.get("source", "https://vinhomes.vn")
        date_val = meta.get("date")
        if not date_val:
            date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})", content)
            date_val = date_match.group(1) if date_match else "01/01/2024"

        clean_body = _clean_content(content)
        header = (
            f"# {title}\n"
            f"**Source:** {source}\n"
            f"**Doc Type:** legal\n"
            f"**Date:** {date_val}\n"
            f"---\n"
        )
        standardized_text = f"{header}\n{clean_body}\n"
        out_file = output_dir / f"{stem}.md"
        out_file.write_text(standardized_text, encoding="utf-8")
        print(f"[Legal] Standardized -> {out_file.name} ({len(standardized_text)} chars)")


def convert_news_articles() -> None:
    """Đọc bài viết từ landing/news và chuẩn hóa sang standardized/news.
    
    Hỗ trợ cả .json và .md; nhóm theo stem để chống trùng lặp, ưu tiên file .json.
    """
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    files_by_stem: dict[str, Path] = {}
    # Lần lượt duyệt: nếu có .md thì lưu, nhưng nếu có .json thì ưu tiên ghi đè để lấy metadata chuẩn
    for path in sorted(news_dir.iterdir()):
        if path.is_file() and not path.name.startswith(".") and path.suffix.lower() in {".json", ".md"}:
            stem = path.stem
            if stem not in files_by_stem or path.suffix.lower() == ".json":
                files_by_stem[stem] = path

    for stem, path in files_by_stem.items():
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            title = data.get("title", stem.replace("-", " ").title())
            source = data.get("url", "https://vinhomes.vn")
            date_val = data.get("date_crawled", "2024-01-01T00:00:00")
            if "T" in date_val:
                date_val = date_val.split("T")[0]
            content = data.get("content_markdown", "")
        else:
            raw_text = path.read_text(encoding="utf-8")
            lines = raw_text.splitlines()
            source = "https://vinhomes.vn"
            for line in lines[:5]:
                m = re.search(r"url\s*:\s*(?:\[.*?\]\()?([^\)\s]+)", line)
                if m:
                    source = m.group(1).strip()
                    break

            title = stem.replace("-", " ").title()
            for line in lines[:8]:
                s = line.strip()
                if s.startswith("# "):
                    title = s[2:].strip()
                    break
                elif s and not s.lower().startswith("url") and len(s) > 10 and not s.endswith((".jpg", ".png")):
                    title = s
                    break

            date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})", raw_text)
            date_val = date_match.group(1) if date_match else "2024-01-01"

            # Bỏ dòng url ở đầu nếu có
            body_lines = [l for l in lines if not l.strip().lower().startswith("url:")]
            content = "\n".join(body_lines)

        clean_body = _clean_content(content)
        if not clean_body:
            continue

        header = (
            f"# {title}\n"
            f"**Source:** {source}\n"
            f"**Doc Type:** news\n"
            f"**Date:** {date_val}\n"
            f"---\n"
        )
        standardized_text = f"{header}\n{clean_body}\n"
        out_file = output_dir / f"{stem}.md"
        out_file.write_text(standardized_text, encoding="utf-8")
        print(f"[News] Standardized -> {out_file.name} ({len(standardized_text)} chars)")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing sang standardized."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Standardization completed. Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()

