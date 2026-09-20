"""Task 3: standardize legal documents and news articles as Markdown."""

import json
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def convert_legal_docs() -> None:
    """Convert supported legal documents to non-empty Markdown files."""
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkItDown()

    for path in sorted(legal_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue
        result = converter.convert(str(path))
        content = result.text_content.strip()
        if not content:
            content = (
                "## Extraction status\n\n"
                "This source document is an image-only scan without an extractable "
                "text layer. The original PDF is retained in the landing zone for "
                "traceability and must be processed with Vietnamese OCR before its "
                "legal provisions can be indexed for question answering. No legal "
                "text has been inferred or fabricated in this standardized record.\n\n"
                f"- Source file: `{path.name}`\n"
                f"- File size: {path.stat().st_size} bytes\n"
                "- Extraction method: MarkItDown\n"
                "- Extraction result: metadata only; OCR required\n"
            )
        output = output_dir / f"{path.stem}.md"
        output.write_text(f"# {path.stem}\n\n{content}\n", encoding="utf-8")
        print(f"Saved: {output}")


def convert_news_articles() -> None:
    """Convert crawled article JSON files while preserving their metadata."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    required = {"url", "title", "date_crawled", "content_markdown"}

    for path in sorted(news_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = required - data.keys()
        if missing:
            raise ValueError(f"{path} is missing fields: {sorted(missing)}")
        content = str(data["content_markdown"]).strip()
        if not content:
            raise ValueError(f"No article content in {path}")
        header = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n---\n\n"
        )
        output = output_dir / f"{path.stem}.md"
        output.write_text(f"{header}{content}\n", encoding="utf-8")
        print(f"Saved: {output}")


def convert_all() -> None:
    """Convert all landing data to standardized Markdown."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
