"""Task 3 — Chuẩn hóa tài liệu pháp lý và bài viết sang Markdown."""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Final


ROOT_DIR = Path(__file__).parent.parent
LANDING_DIR = ROOT_DIR / "data" / "landing"
OUTPUT_DIR = ROOT_DIR / "data" / "standardized"
MIN_CONTENT_LENGTH: Final = 200
MIN_PDF_TEXT_LENGTH: Final = 500

LEGAL_METADATA: Final = {
    "luat_du_lich_09_2017_qh14": {
        "title": "Luật Du lịch số 09/2017/QH14",
        "url": "https://vanban.chinhphu.vn/?docid=190290&pageid=27160",
    },
    "nghi_dinh_168_2017_nd_cp_huong_dan_luat_du_lich": {
        "title": "Nghị định 168/2017/NĐ-CP quy định chi tiết Luật Du lịch",
        "url": "https://vanban.chinhphu.vn/?docid=193059&pageid=27160",
    },
    "quyet_dinh_147_qd_ttg_chien_luoc_phat_trien_du_lich_2030": {
        "title": "Quyết định 147/QĐ-TTg về Chiến lược phát triển du lịch đến 2030",
        "url": "https://vanban.chinhphu.vn/?docid=198927&pageid=27160",
    },
}


def _clean_text(text: str) -> str:
    text = text.replace("\x0c", "\n\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _write_atomic(path: Path, content: str) -> None:
    content = content.strip() + "\n"
    if len(content) < MIN_CONTENT_LENGTH:
        raise ValueError(f"Nội dung chuẩn hóa quá ngắn: {path.name}")
    temporary_path = path.with_suffix(path.suffix + ".part")
    try:
        temporary_path.write_text(content, encoding="utf-8")
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _is_fresh(source: Path, output: Path) -> bool:
    try:
        return (
            output.stat().st_mtime_ns >= source.stat().st_mtime_ns
            and len(output.read_text(encoding="utf-8").strip()) >= MIN_CONTENT_LENGTH
        )
    except (OSError, UnicodeError):
        return False


def _convert_with_markitdown(path: Path) -> str:
    try:
        from markitdown import MarkItDown

        result = MarkItDown().convert(path)
        return _clean_text(result.text_content)
    except Exception:
        return ""


def _ocr_pdf(path: Path) -> str:
    """OCR PDF scan bằng Poppler và Tesseract với mô hình tiếng Việt."""
    missing = [
        command
        for command in ("pdftoppm", "tesseract")
        if shutil.which(command) is None
    ]
    if missing:
        commands = ", ".join(missing)
        raise RuntimeError(
            f"PDF {path.name} không có text layer và thiếu công cụ OCR: {commands}. "
            "Cài tesseract-ocr, tesseract-ocr-vie và poppler-utils."
        )

    with tempfile.TemporaryDirectory(prefix="task3_ocr_") as temp_dir:
        image_prefix = Path(temp_dir) / "page"
        subprocess.run(
            [
                "pdftoppm",
                "-jpeg",
                "-r",
                "180",
                str(path),
                str(image_prefix),
            ],
            check=True,
            capture_output=True,
        )

        pages: list[str] = []
        for page_number, image_path in enumerate(
            sorted(Path(temp_dir).glob("page-*.jpg")),
            1,
        ):
            result = subprocess.run(
                [
                    "tesseract",
                    str(image_path),
                    "stdout",
                    "-l",
                    "vie+eng",
                    "--psm",
                    "6",
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            page_text = _clean_text(result.stdout)
            if page_text:
                pages.append(f"## Trang {page_number}\n\n{page_text}")

    content = "\n\n".join(pages)
    if len(content) < MIN_PDF_TEXT_LENGTH:
        raise ValueError(f"OCR không lấy đủ nội dung từ {path.name}")
    return content


def _convert_legal_document(path: Path) -> str:
    content = _convert_with_markitdown(path)
    if path.suffix.lower() == ".pdf" and len(content) < MIN_PDF_TEXT_LENGTH:
        print(f"PDF scan, đang OCR: {path.name}")
        content = _ocr_pdf(path)
    if len(content) < MIN_CONTENT_LENGTH:
        raise ValueError(f"Không trích xuất được nội dung từ {path.name}")
    return content


def convert_legal_docs() -> list[Path]:
    """Convert PDF/DOC/DOCX trong landing/legal sang Markdown."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    source_paths = sorted(
        path
        for path in legal_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".pdf", ".doc", ".docx"}
    )
    if not source_paths:
        raise RuntimeError(f"Không có tài liệu pháp lý trong {legal_dir}")

    outputs: list[Path] = []
    for source in source_paths:
        output = output_dir / f"{source.stem}.md"
        if _is_fresh(source, output):
            print(f"Đã có: {output.relative_to(ROOT_DIR)}")
            outputs.append(output)
            continue

        metadata = LEGAL_METADATA.get(
            source.stem,
            {
                "title": source.stem.replace("_", " ").title(),
                "url": None,
            },
        )
        body = _convert_legal_document(source)
        header = (
            f"# {metadata['title']}\n\n"
            f"**Source file:** {source.name}\n\n"
            f"**Source URL:** {metadata['url'] or 'Không có'}\n\n"
            "---\n\n"
        )
        _write_atomic(output, header + body)
        print(f"Đã lưu: {output.relative_to(ROOT_DIR)}")
        outputs.append(output)
    return outputs


def _validate_news(data: object, source: Path) -> dict[str, str]:
    if not isinstance(data, dict):
        raise ValueError(f"{source.name} phải chứa một JSON object")
    required = ("url", "title", "date_crawled", "content_markdown")
    for field in required:
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError(f"{source.name} thiếu trường hợp lệ: {field}")
    if len(data["content_markdown"].strip()) < MIN_CONTENT_LENGTH:
        raise ValueError(f"Nội dung quá ngắn trong {source.name}")
    return data


def convert_news_articles() -> list[Path]:
    """Convert JSON trong landing/news sang Markdown có metadata."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    source_paths = sorted(news_dir.glob("*.json"))
    if not source_paths:
        raise RuntimeError(f"Không có bài viết JSON trong {news_dir}")

    outputs: list[Path] = []
    for source in source_paths:
        output = output_dir / f"{source.stem}.md"
        if _is_fresh(source, output):
            print(f"Đã có: {output.relative_to(ROOT_DIR)}")
            outputs.append(output)
            continue

        try:
            raw_data = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"JSON không hợp lệ: {source.name}") from error
        data = _validate_news(raw_data, source)
        markdown = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n"
            "---\n\n"
            f"{data['content_markdown'].strip()}\n"
        )
        _write_atomic(output, markdown)
        print(f"Đã lưu: {output.relative_to(ROOT_DIR)}")
        outputs.append(output)
    return outputs


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing và xác nhận số lượng đầu ra."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    legal = convert_legal_docs()
    news = convert_news_articles()
    print(
        f"Hoàn tất: {len(legal)} tài liệu pháp lý và {len(news)} bài viết "
        f"tại {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    convert_all()
