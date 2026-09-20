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

Ghi chú của nhóm:
    - Mỗi file .md có front matter (doc_id, title, source_url, doc_type,
      source_file...) để từ Markdown lần ngược về file landing và URL công khai.
    - PDF scan: MarkItDown chỉ đọc được lớp OCR sẵn có trong file và thường
      sai nặng với tiếng Việt. Khi chữ trích ra không đọc được, dùng Gemini
      (GEMINI_API_KEY trong .env) để chép lại nguyên văn từ ảnh trang.
      Kết quả được giữ lại trong standardized/; muốn chạy OCR lại thì xóa file .md.
"""

import csv
import json
import os
import re
import time
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"
LEGAL_MANIFEST = LANDING_DIR / "legal" / "sources.csv"

LEGAL_SUFFIXES = {".pdf", ".doc", ".docx"}
OCR_MARK = 'extraction: "gemini-ocr"'

# Từ phổ biến trong tiếng Việt; tỉ lệ thấp nghĩa là chữ trích ra bị nát (bản scan).
_VI_COMMON = {
    "của", "và", "các", "là", "có", "được", "cho", "trong", "tại", "để",
    "không", "theo", "với", "khi", "một", "thư", "viện", "tài", "liệu",
    "độc", "giả", "này", "những", "về", "do", "sẽ", "đã", "người",
}

_OCR_PROMPT = (
    "Đây là bản scan một văn bản tiếng Việt. Hãy chép lại NGUYÊN VĂN toàn bộ nội dung "
    "ra Markdown: giữ đúng dấu tiếng Việt, số hiệu, ngày tháng, số tiền; bảng biểu chuyển "
    "thành bảng Markdown; danh sách giữ nguyên đánh số. Không tóm tắt, không thêm hay bớt "
    "ý, không bình luận. Chữ không đọc rõ thì ghi [không rõ]. Bỏ qua con dấu và chữ ký. "
    "Chỉ trả về nội dung Markdown."
)


def _front_matter(fields: dict) -> str:
    """Front matter dạng YAML; json.dumps cho giá trị chuỗi đã đúng quy tắc quote của YAML."""
    lines = [f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fields.items()]
    return "---\n" + "\n".join(lines) + "\n---\n\n"


def _is_readable(text: str) -> bool:
    """False nếu chữ trích ra quá ít hoặc không giống tiếng Việt (PDF scan bị OCR sai)."""
    words = re.findall(r"\w+", text.lower())
    if len(words) < 30:
        return False
    return sum(word in _VI_COMMON for word in words) / len(words) >= 0.08


def _transcribe_with_gemini(path: Path) -> str:
    from dotenv import load_dotenv
    from google import genai
    from google.genai import errors, types

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("PDF scan cần GEMINI_API_KEY trong .env để đọc chữ")
    client = genai.Client(api_key=api_key)
    pdf = types.Part.from_bytes(data=path.read_bytes(), mime_type="application/pdf")
    config = types.GenerateContentConfig(temperature=0)

    # Gemini thi thoảng trả 503 khi quá tải; thử lại vài lần trước khi bỏ cuộc.
    for attempt, delay in enumerate((5, 20, 45, None), 1):
        try:
            response = client.models.generate_content(
                model=os.getenv("OCR_MODEL") or "gemini-3.6-flash",
                contents=[pdf, _OCR_PROMPT],
                config=config,
            )
            return (response.text or "").strip()
        except errors.ServerError as error:
            if delay is None:
                raise
            print(f"  Gemini lỗi tạm thời ({error.code}), thử lại lần {attempt} sau {delay}s")
            time.sleep(delay)


def _read_manifest() -> dict[str, dict]:
    if not LEGAL_MANIFEST.exists():
        return {}
    with LEGAL_MANIFEST.open(encoding="utf-8", newline="") as handle:
        return {row["file"]: row for row in csv.DictReader(handle)}


def _prune_stale(output_dir: Path, keep_stems: set[str]) -> None:
    """Xóa .md không còn file landing tương ứng để chạy lại không để lại bản thừa."""
    for stale in output_dir.glob("*.md"):
        if stale.stem not in keep_stems:
            stale.unlink()
            print(f"Removed stale: {stale.name}")


def convert_legal_docs() -> None:
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest()
    converter = MarkItDown()

    sources = sorted(p for p in legal_dir.iterdir() if p.suffix.lower() in LEGAL_SUFFIXES)
    for path in sources:
        target = output_dir / f"{path.stem}.md"
        info = manifest.get(path.name, {})
        text = converter.convert(str(path)).text_content.strip()
        method = "markitdown"

        if not _is_readable(text):
            if target.exists() and OCR_MARK in target.read_text(encoding="utf-8"):
                print(f"Kept (OCR đã có): {target.name}")
                continue
            print(f"Scan/OCR sai, đọc bằng Gemini: {path.name}")
            try:
                text = _transcribe_with_gemini(path)
            except Exception as error:
                # Không dừng cả pipeline vì một file; chạy lại sẽ thử tiếp file này.
                print(f"Failed: {path.name} — {error}")
                continue
            method = "gemini-ocr"

        if not text:
            print(f"Skipped (rỗng): {path.name}")
            continue

        title = info.get("title") or path.stem
        header = _front_matter({
            "doc_id": path.stem,
            "title": title,
            "doc_type": "legal",
            "source_url": info.get("pdf_url", ""),
            "source_page": info.get("source_page", ""),
            "source_file": f"data/landing/legal/{path.name}",
            "extraction": method,
        })
        target.write_text(header + f"# {title}\n\n" + text + "\n", encoding="utf-8")
        print(f"Saved: {target.name} ({method})")

    _prune_stale(output_dir, {p.stem for p in sources})


def convert_news_articles() -> None:
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(news_dir.glob("*.json"))
    for path in sources:
        data = json.loads(path.read_text(encoding="utf-8"))
        content = data["content_markdown"].strip()
        if not content:
            print(f"Skipped (rỗng): {path.name}")
            continue
        header = _front_matter({
            "doc_id": path.stem,
            "title": data["title"],
            "doc_type": "news",
            "source_url": data["url"],
            "date_crawled": data["date_crawled"],
            "source_file": f"data/landing/news/{path.name}",
        })
        (output_dir / f"{path.stem}.md").write_text(
            header + f"# {data['title']}\n\n" + content + "\n", encoding="utf-8"
        )
        print(f"Saved: {path.stem}.md")

    _prune_stale(output_dir, {p.stem for p in sources})


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
