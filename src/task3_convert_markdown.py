"""Normalize original legal PDFs and article JSON files into Markdown."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

from src.task1_collect_legal_docs import MANIFEST_PATH


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _yaml_string(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _frontmatter(metadata: dict) -> str:
    lines = ["---"]
    lines.extend(f"{key}: {_yaml_string(value)}" for key, value in metadata.items())
    lines.extend(["---", ""])
    return "\n".join(lines)


def _normalize_pdf_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def convert_legal_docs() -> None:
    """Extract every PDF and retain provenance in YAML frontmatter."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        item["filename"]: item
        for item in json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    }

    for path in sorted(legal_dir.glob("*.pdf")):
        source = manifest.get(path.name)
        if source is None:
            raise ValueError(f"Missing provenance entry for {path.name}")
        reader = PdfReader(path)
        page_texts = []
        for index, page in enumerate(reader.pages, 1):
            content = _normalize_pdf_text(page.extract_text() or "")
            if content:
                page_texts.append(f"## Trang {index}\n\n{content}")
        text = "\n\n".join(page_texts)
        if len(text) < 200:
            raise ValueError(f"Extracted legal text is too short: {path.name}")

        metadata = {
            "title": source["title"],
            "source": path.name,
            "doc_type": "legal",
            "url": source["landing_page"],
            "download_url": source["url"],
            "document_number": source["document_number"],
            "issued_date": source["issued_date"],
            "publisher": source["publisher"],
            "sha256": source["sha256"],
            "pages": len(reader.pages),
        }
        output = output_dir / f"{path.stem}.md"
        output.write_text(
            _frontmatter(metadata) + f"# {source['title']}\n\n" + text + "\n",
            encoding="utf-8",
        )
        print(f"Saved: {output}")


def convert_news_articles() -> None:
    """Convert all article JSON files and retain source metadata."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    required = {"url", "title", "date_crawled", "content_markdown"}

    for path in sorted(news_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = required - data.keys()
        if missing:
            raise ValueError(f"{path.name} is missing: {sorted(missing)}")
        content = str(data["content_markdown"]).strip()
        if len(content) < 200:
            raise ValueError(f"Article text is too short: {path.name}")
        metadata = {
            "title": data["title"],
            "source": path.name,
            "doc_type": "news",
            "url": data["url"],
            "date_published": data.get("date_published"),
            "date_crawled": data["date_crawled"],
            "publisher": data.get("publisher"),
        }
        output = output_dir / f"{path.stem}.md"
        output.write_text(
            _frontmatter(metadata) + f"# {data['title']}\n\n" + content + "\n",
            encoding="utf-8",
        )
        print(f"Saved: {output}")


def convert_all() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
