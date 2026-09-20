"""Task 3 - Convert landing data into standardized Markdown files.

Rules:
    - Keep originals under data/landing unchanged.
    - Write Markdown only under data/standardized/{legal,news}.
    - Legal and news outputs both keep title and source in a header.
"""

import json
from pathlib import Path

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

LEGAL_SOURCES = {
    "NIST_AI_600-1_GenAI_Profile.pdf": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf",
    "NIST_AI_100-4_Prompt_Engineering.pdf": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-4.pdf",
    "Prompt_Injection_Formalization_Benchmarking.pdf": "https://arxiv.org/pdf/2302.12173",
}


def _write_markdown(path: Path, title: str, source: str, body: str) -> None:
    body = body.strip()
    if len(body) < 200:
        raise ValueError(f"converted content is shorter than 200 chars: {path.name}")

    header = (
        f"# {title}\n\n"
        f"**Source:** {source}\n\n"
        f"---\n\n"
    )
    path.write_text(header + body, encoding="utf-8")


def convert_legal_docs() -> None:
    """Convert PDF/DOCX originals into standardized/legal/*.md."""
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    converter = MarkItDown()
    valid_suffixes = {".pdf", ".doc", ".docx"}

    for path in sorted(legal_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in valid_suffixes:
            continue

        try:
            result = converter.convert(str(path))
            body = getattr(result, "text_content", None) or ""
            title = path.stem.replace("_", " ")
            source = LEGAL_SOURCES.get(path.name, path.as_posix())
            destination = output_dir / f"{path.stem}.md"
            _write_markdown(destination, title, source, body)
            print(f"Converted legal: {destination.name}")
        except Exception as error:
            print(f"Failed legal {path.name}: {error}")


def convert_news_articles() -> None:
    """Convert landing JSON articles into standardized/news/*.md."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(news_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            title = str(data.get("title") or "").strip() or path.stem
            source = str(data.get("url") or "").strip()
            body = str(data.get("content_markdown") or "")

            destination = output_dir / f"{path.stem}.md"
            _write_markdown(destination, title, source, body)
            print(f"Converted news: {destination.name}")
        except Exception as error:
            print(f"Failed news {path.name}: {error}")


def convert_all() -> None:
    """Convert all landing data to standardized Markdown."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
