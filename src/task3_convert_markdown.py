import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LANDING_DIR = BASE_DIR / "data" / "landing"
OUTPUT_DIR = BASE_DIR / "data" / "standardized"


def _extract_doc_text_fallback(file_path: Path) -> str:
    """Hàm fallback đọc nội dung cho file .doc cũ nếu MarkItDown không hỗ trợ trực tiếp."""
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
        for enc in ["utf-16le", "utf-8", "windows-1258", "cp1252"]:
            try:
                decoded = content_bytes.decode(enc, errors="ignore")
                extracted = re.findall(r"[\w\s,.;:/?!@#$%^&*()_\-+=\[\]\"']{30,}", decoded)
                if extracted and len(" ".join(extracted)) > 200:
                    return "\n\n".join(extracted)
            except Exception:
                continue
    except Exception:
        pass

    return ""


def _convert_doc_to_docx_with_libreoffice(doc_path: Path) -> Path | None:
    """Chuyển .doc sang .docx bằng LibreOffice headless để MarkItDown đọc được."""
    if not shutil.which("libreoffice"):
        return None
    try:
        temp_dir = Path(tempfile.mkdtemp())
        cmd = [
            "libreoffice",
            "--headless",
            "--convert-to",
            "docx",
            str(doc_path),
            "--outdir",
            str(temp_dir),
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if result.returncode == 0:
            converted_docx = temp_dir / f"{doc_path.stem}.docx"
            if converted_docx.exists():
                return converted_docx
    except Exception as e:
        print(f" -> LibreOffice convert thất bại: {e}")
    return None


def _extract_doc_text_with_antiword(file_path: Path) -> str:
    """Fallback dùng antiword để đọc văn bản .doc tiếng Việt."""
    if not shutil.which("antiword"):
        return ""
    try:
        proc = subprocess.run(
            ["antiword", "-m", "UTF-8.txt", str(file_path)],  # Xuất UTF-8 sạch
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=15,
        )
        return proc.stdout.strip()
    except Exception:
        try:
            proc = subprocess.run(
                ["antiword", str(file_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            return proc.stdout.strip()
        except Exception:
            return ""


def parse_legal_file(path: Path, converter) -> str:
    """Parse tài liệu pháp luật (PDF, DOCX, DOC)."""
    text_content = ""
    temp_docx = None

    # Nếu là .doc legacy: Ưu tiên convert sang .docx tạm để đưa qua MarkItDown
    if path.suffix.lower() == ".doc":
        temp_docx = _convert_doc_to_docx_with_libreoffice(path)
        target_path = temp_docx if temp_docx else path
    else:
        target_path = path

    # 1. Thử convert bằng MarkItDown
    if converter and target_path.suffix.lower() in [".pdf", ".docx"]:
        try:
            res = converter.convert(str(target_path))
            if res and res.text_content:
                text_content = res.text_content.strip()
        except Exception as e:
            print(f" -> Lỗi MarkItDown: {e}")

    # 2. Fallback nếu vẫn là .doc và chưa có text (hoặc LibreOffice chưa cài)
    if not text_content and path.suffix.lower() == ".doc":
        print(f" -> Dùng antiword fallback cho {path.name}...")
        text_content = _extract_doc_text_with_antiword(path)

    # Dọn dẹp file tạm .docx
    if temp_docx and temp_docx.exists():
        shutil.rmtree(temp_docx.parent, ignore_errors=True)

    return text_content


def convert_legal_docs() -> None:
    """Convert PDF/DOC/DOCX trong landing/legal sang standardized/legal."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not legal_dir.exists():
        print(f"[Legal] Bỏ qua: Thư mục {legal_dir} không tồn tại.")
        return

    converter = None
    try:
        from markitdown import MarkItDown
        converter = MarkItDown()
    except Exception as e:
        print(f"[Notice] MarkItDown chưa được cài: {e}")

    valid_exts = {".pdf", ".doc", ".docx"}
    for path in legal_dir.iterdir():
        if path.suffix.lower() not in valid_exts:
            continue

        target_file = output_dir / f"{path.stem}.md"

        # Chống chạy lại trùng lặp (nếu file đã convert và mới hơn file gốc)
        if target_file.exists() and target_file.stat().st_size > 0:
            if target_file.stat().st_mtime >= path.stat().st_mtime:
                print(f"[Legal] Đã tồn tại, bỏ qua: {target_file.name}")
                continue

        print(f"[Legal] Đang convert: {path.name}...")
        text_content = parse_legal_file(path, converter)

        # Không tạo file rỗng
        if not text_content.strip():
            print(f" [!] Bỏ qua file rỗng hoặc không đọc được: {path.name}")
            continue

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