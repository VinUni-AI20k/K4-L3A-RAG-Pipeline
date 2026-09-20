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


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def convert_legal_docs() -> None:
    """Chuyển PDF scan thành Markdown bằng Docling + EasyOCR chạy CPU."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import EasyOcrOptions, OcrMode, PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    source_files = sorted(
        path
        for path in legal_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".pdf", ".doc", ".docx"}
    )
    if not source_files:
        print(f"No legal documents found in: {legal_dir}")
        return

    for path in source_files:
        options = PdfPipelineOptions()
        options.do_ocr = True
        options.ocr_options = EasyOcrOptions(mode=OcrMode.FULL_PAGE, lang=["vi", "en"], use_gpu=False)
        converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
        content = converter.convert(path).document.export_to_markdown().strip()
        if not content:
            raise ValueError(f"OCR produced empty content: {path}")
        output = output_dir / f"{path.stem}.md"
        header = f"# {path.stem}\n\n**Source file:** {path.name}\n\n---\n\n"
        output.write_text(header + content + "\n", encoding="utf-8")
        print(f"Converted: {path.name} -> {output}")


def convert_news_articles() -> None:
    """Chuyển JSON đã crawl thành Markdown, giữ metadata nguồn ở đầu file."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    source_files = sorted(news_dir.glob("*.json"))
    if not source_files:
        print(f"No news articles found in: {news_dir}; skipping news conversion.")
        return

    required_fields = {"url", "title", "date_crawled", "content_markdown"}
    for path in source_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = required_fields - data.keys()
        if missing:
            raise ValueError(f"Missing fields {sorted(missing)} in: {path}")

        content = str(data["content_markdown"]).strip()
        if not content:
            raise ValueError(f"Article content is empty: {path}")

        header = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n---\n\n"
        )
        output = output_dir / f"{path.stem}.md"
        output.write_text(header + content + "\n", encoding="utf-8")
        print(f"Converted: {path.name} -> {output}")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
