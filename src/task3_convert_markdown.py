"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX (có fallback cho .doc legacy).
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cài đặt:
    Dependency MarkItDown đã được khai báo trong pyproject.toml.
    
-> Hoặc dùng công cụ nào bạn quen khác Markitdown
"""

import json
from pathlib import Path
import re
import subprocess

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _extract_doc_text_fallback(file_path: Path) -> str:
    """Hàm fallback đọc nội dung cho file .doc cũ nếu MarkItDown không hỗ trợ trực tiếp."""
    # Thử qua antiword (nếu có trên Linux/macOS)
    try:
        proc = subprocess.run(
            ["antiword", str(file_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        if proc.stdout.strip():
            return proc.stdout
    except Exception:
        pass

    # Thử trích xuất các chuỗi text có nghĩa từ binary doc
    try:
        content_bytes = file_path.read_bytes()
        # Thử decode UTF-16LE hoặc Windows-1258 / UTF-8
        for enc in ["utf-16le", "utf-8", "windows-1258", "cp1252"]:
            try:
                decoded = content_bytes.decode(enc, errors="ignore")
                # Lọc các đoạn text dài trên 30 ký tự
                extracted = re.findall(r"[\w\s,.;:/?!@#$%^&*()_\-+=\[\]\"']{30,}", decoded)
                if extracted and len(" ".join(extracted)) > 200:
                    return "\n\n".join(extracted)
            except Exception:
                continue
    except Exception:
        pass

    return ""


def convert_legal_docs() -> None:
    """Convert PDF/DOC/DOCX trong landing/legal vào standardized/legal."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not legal_dir.exists():
        print(f"[Legal] Bỏ qua: Thư mục {legal_dir} không tồn tại.")
        return

    # Khởi tạo MarkItDown nếu có
    converter = None
    try:
        from markitdown import MarkItDown
        converter = MarkItDown()
    except Exception as e:
        print(f"[Notice] MarkItDown chưa khởi tạo được ({e}), sử dụng fallback.")

    valid_exts = {".pdf", ".doc", ".docx"}
    for path in legal_dir.iterdir():
        if path.suffix.lower() not in valid_exts:
            continue

        target_file = output_dir / f"{path.stem}.md"
        text_content = ""

        print(f"[Legal] Đang convert: {path.name}...")

        # 1. Thử convert bằng MarkItDown
        if converter:
            try:
                res = converter.convert(str(path))
                if res and res.text_content:
                    text_content = res.text_content.strip()
            except Exception as conv_err:
                print(f" -> MarkItDown không đọc được file {path.name} ({conv_err}). Chuyển fallback.")

        # 2. Fallback nếu MarkItDown không xử lý được (đặc biệt với .doc legacy)
        if not text_content:
            text_content = _extract_doc_text_fallback(path)

        if not text_content.strip():
            print(f" [!] Cảnh báo: Không thể trích xuất nội dung từ {path.name}. Vui lòng đổi sang .docx hoặc .pdf.")
            continue

        # Định dạng header chuẩn cho file văn bản quy định
        doc_title = path.stem.replace("_", " ").title()
        metadata_header = (
            f"# {doc_title}\n\n"
            f"- **Loại tài liệu:** Văn bản quy phạm pháp luật / Quy chế\n"
            f"- **Tên file gốc:** `{path.name}`\n\n"
            f"---\n\n"
        )

        target_file.write_text(metadata_header + text_content, encoding="utf-8")
        print(f" -> Đã lưu: {target_file.name}")


def convert_news_articles() -> None:
    """Convert các file JSON trong landing/news sang standardized/news."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not news_dir.exists():
        print(f"[News] Bỏ qua: Thư mục {news_dir} không tồn tại.")
        return

    json_files = list(news_dir.glob("*.json"))
    for path in json_files:
        try:
            raw_text = path.read_text(encoding="utf-8").strip()
            if not raw_text:
                continue

            data = json.loads(raw_text)
            title = data.get("title", path.stem).strip()
            url = data.get("url", "Unknown")
            crawled_at = data.get("date_crawled", "Unknown")
            content = data.get("content_markdown", "").strip()

            if not content:
                print(f" [!] Bỏ qua file rỗng: {path.name}")
                continue

            # Chuẩn hóa header giữ nguyên source/crawled date phục vụ citation
            header = (
                f"# {title}\n\n"
                f"- **Source:** {url}\n"
                f"- **Crawled:** {crawled_at}\n\n"
                f"---\n\n"
            )

            # Loại bỏ trùng tiêu đề cấp 1 nếu trong content_markdown đã có sẵn
            if content.startswith(f"# {title}"):
                content = content[len(f"# {title}"):].strip()

            target_file = output_dir / f"{path.stem}.md"
            target_file.write_text(header + content, encoding="utf-8")
            print(f"[News] Đã convert: {path.name} -> {target_file.name}")

        except Exception as e:
            print(f" [x] Lỗi khi xử lý file {path.name}: {e}")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"\n[OK] Hoàn tất! Markdown đã được lưu tại: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()