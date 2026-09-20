"""Chuẩn hóa sách PDF scan và bài viết JSON thành Markdown có nguồn rõ ràng."""

import io
import json
import os
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).parent.parent
LANDING_DIR = ROOT / "data" / "landing"
OUTPUT_DIR = ROOT / "data" / "standardized"
TESSDATA_DIR = Path(os.getenv("TESSDATA_DIR", ROOT / ".cache" / "tessdata"))
OCR_DPI = 180
BOOK_TITLES = {
    "10": "Vật lí 10 – Kết nối tri thức với cuộc sống",
    "11": "Vật lí 11 – Kết nối tri thức với cuộc sống",
    "12": "Vật lí 12 – Kết nối tri thức với cuộc sống",
}


def _tesseract_command() -> str:
    configured = os.getenv("TESSERACT_CMD")
    candidates = [configured, shutil.which("tesseract"), r"C:\Program Files\Tesseract-OCR\tesseract.exe"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise RuntimeError("Không tìm thấy Tesseract OCR. Cài Tesseract hoặc đặt TESSERACT_CMD.")


def _clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    return "\n".join(" ".join(line.split()) for line in text.splitlines()).strip()


def _ocr_page(page, tesseract: str) -> str:
    image = page.to_image(resolution=OCR_DPI).original
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    command = [tesseract, "stdin", "stdout", "--tessdata-dir", str(TESSDATA_DIR), "-l", "vie"]
    result = subprocess.run(command, input=stream.getvalue(), capture_output=True, timeout=90)
    if result.returncode:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Tesseract lỗi: {error}")
    return _clean_text(result.stdout.decode("utf-8", errors="replace"))


def _write_markdown(path: Path, content: str) -> None:
    if len(content.strip()) < 200:
        raise ValueError(f"Markdown quá ngắn hoặc rỗng: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", suffix=".tmp", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def convert_legal_docs() -> None:
    """OCR ba sách PDF, giữ thứ tự và mốc trang PDF trong Markdown."""
    pdfs = sorted((LANDING_DIR / "legal").glob("*.pdf"))
    if len(pdfs) < 3:
        raise ValueError("Cần ít nhất ba PDF trong data/landing/legal")
    if not (TESSDATA_DIR / "vie.traineddata").is_file():
        raise RuntimeError(f"Thiếu mô hình OCR tiếng Việt: {TESSDATA_DIR / 'vie.traineddata'}")
    tesseract = _tesseract_command()

    for source in pdfs:
        with pdfplumber.open(source) as document:
            grade = source.stem if source.stem in BOOK_TITLES else ""
            title = BOOK_TITLES.get(source.stem, source.stem)
            parts = [
                f"# {title}", f"**Source file:** {source.name}", "**Document type:** textbook",
                f"**Grade:** {grade or 'unknown'}", "**Publisher:** Nhà xuất bản Giáo dục Việt Nam",
                f"**PDF pages:** {len(document.pages)}",
                f"**Extraction:** PDF text layer or Tesseract Vietnamese OCR at {OCR_DPI} dpi",
                "**OCR warning:** Verify formulas, figures and tables against the original PDF.",
            ]
            text_pages = 0
            for index, page in enumerate(document.pages, 1):
                extracted = _clean_text(page.extract_text() or "")
                if len(extracted) < 50:
                    extracted = _ocr_page(page, tesseract)
                if extracted:
                    parts.append(f"\n## PDF page {index}\n\n<!-- pdf_page: {index} -->\n\n{extracted}")
                    text_pages += 1
                if index % 10 == 0 or index == len(document.pages):
                    print(f"{source.name}: {index}/{len(document.pages)} pages", flush=True)
            if text_pages < len(document.pages) // 2:
                raise ValueError(f"OCR chỉ đọc được {text_pages}/{len(document.pages)} trang: {source}")
        output = OUTPUT_DIR / "legal" / f"{source.stem}.md"
        _write_markdown(output, "\n\n".join(parts) + "\n")
        print(f"Saved: {output} ({text_pages} pages with text)", flush=True)


def convert_news_articles() -> None:
    """Giữ metadata và phần nội dung của mỗi bài JSON trong một file Markdown."""
    articles = sorted((LANDING_DIR / "news").glob("*.json"))
    if len(articles) < 5:
        raise ValueError("Cần ít nhất năm JSON trong data/landing/news")
    required = ("url", "title", "date_crawled", "content_markdown")
    for source in articles:
        article = json.loads(source.read_text(encoding="utf-8"))
        if any(not isinstance(article.get(key), str) or not article[key].strip() for key in required):
            raise ValueError(f"Thiếu metadata hoặc nội dung bài viết: {source}")
        title = article["title"].strip()
        body = article["content_markdown"].strip()
        if body.startswith(f"# {title}"):
            body = body[len(f"# {title}"):].strip()
        parts = [
            f"# {title}", f"**Source URL:** {article['url']}",
            f"**Crawled:** {article['date_crawled']}", "**Document type:** public article",
        ]
        for key, label in (("content_scope", "Content scope"), ("license", "License")):
            if article.get(key):
                parts.append(f"**{label}:** {article[key]}")
        output = OUTPUT_DIR / "news" / f"{source.stem}.md"
        _write_markdown(output, "\n\n".join(parts) + f"\n\n---\n\n{body}\n")
        print(f"Saved: {output}", flush=True)


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}", flush=True)


if __name__ == "__main__":
    convert_all()
