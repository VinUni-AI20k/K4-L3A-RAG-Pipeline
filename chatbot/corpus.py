"""Load the legal corpus and split it into citable chunks.

Chunking is article-aware: Vietnamese statutes and the sample contract are
organised as numbered "Điều N. ..." articles, so splitting on that boundary
keeps each chunk semantically whole and gives a natural citation label
("Điều 25 - luat-kinh-doanh-bds.md") instead of an arbitrary character
window.
"""

import re
from dataclasses import dataclass

from . import config

ARTICLE_RE = re.compile(r"^\*{0,2}(Điều\s+\d+[a-zđA-ZĐ]?\.\s*.*)\*{0,2}\s*$")


@dataclass
class Chunk:
    id: str
    content: str
    title: str
    source: str


def _ensure_markdown_corpus() -> None:
    """Convert PDF/DOCX in data/landing/legal if standardized markdown is missing."""
    config.STANDARDIZED_LEGAL_DIR.mkdir(parents=True, exist_ok=True)
    existing = {p.stem for p in config.STANDARDIZED_LEGAL_DIR.glob("*.md")}
    landing_files = [
        p
        for p in config.LANDING_LEGAL_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".pdf", ".doc", ".docx"}
    ]
    missing = [p for p in landing_files if p.stem not in existing]
    if not missing:
        return

    from markitdown import MarkItDown

    converter = MarkItDown()
    for path in missing:
        try:
            result = converter.convert(str(path))
        except Exception:
            continue
        text = result.text_content.strip()
        if not text:
            continue
        header = f"# {path.stem}\n\n**Source file:** {path.name}\n\n---\n\n"
        out_path = config.STANDARDIZED_LEGAL_DIR / f"{path.stem}.md"
        out_path.write_text(header + text + "\n", encoding="utf-8")


def _split_into_articles(text: str) -> list[tuple[str, str]]:
    """Split markdown text into (title, body) pairs on 'Điều N.' boundaries."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title = "Mở đầu"
    current_body: list[str] = []
    for line in lines:
        match = ARTICLE_RE.match(line.strip())
        if match:
            if current_body:
                sections.append((current_title, current_body))
            current_title = match.group(1).strip(" *")
            current_body = []
        else:
            current_body.append(line)
    if current_body:
        sections.append((current_title, current_body))
    return [(title, "\n".join(body).strip()) for title, body in sections if "\n".join(body).strip()]


def _split_on_separator(text: str, separator: str) -> list[str]:
    if separator == "":
        return list(text)
    return [part for part in text.split(separator) if part != ""]


def _recursive_split(text: str, separators: list[str]) -> list[str]:
    """Minimal, dependency-free stand-in for a recursive character splitter."""
    if len(text) <= config.CHUNK_MAX_CHARS:
        return [text]

    separator, *rest = separators
    pieces = _split_on_separator(text, separator)
    if len(pieces) == 1 and rest:
        return _recursive_split(text, rest)

    chunks: list[str] = []
    buffer = ""
    for piece in pieces:
        candidate = buffer + separator + piece if buffer else piece
        if len(candidate) <= config.CHUNK_MAX_CHARS:
            buffer = candidate
        else:
            if buffer:
                chunks.append(buffer)
            if len(piece) > config.CHUNK_MAX_CHARS and rest:
                chunks.extend(_recursive_split(piece, rest))
                buffer = ""
            else:
                buffer = piece
    if buffer:
        chunks.append(buffer)

    if config.CHUNK_OVERLAP and len(chunks) > 1:
        overlapped = [chunks[0]]
        for chunk in chunks[1:]:
            tail = overlapped[-1][-config.CHUNK_OVERLAP :]
            overlapped.append(tail + chunk)
        return overlapped
    return chunks


def _sub_split(body: str) -> list[str]:
    if len(body) <= config.CHUNK_MAX_CHARS:
        return [body]
    return _recursive_split(body, ["\n\n", "\n", ". ", " "])


def load_chunks() -> list[Chunk]:
    """Load every standardized legal document and split it into Chunk objects."""
    _ensure_markdown_corpus()

    chunks: list[Chunk] = []
    for path in sorted(config.STANDARDIZED_LEGAL_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for section_index, (title, body) in enumerate(_split_into_articles(text)):
            pieces = _sub_split(body)
            for piece_index, piece in enumerate(pieces):
                if not piece.strip():
                    continue
                chunk_id = f"{path.stem}::{section_index}-{piece_index}"
                chunks.append(
                    Chunk(id=chunk_id, content=piece.strip(), title=title, source=path.name)
                )
    return chunks


if __name__ == "__main__":
    result = load_chunks()
    print(f"Loaded {len(result)} chunks from {config.STANDARDIZED_LEGAL_DIR}")
    for sample in result[:3]:
        print("-", sample.id, "|", sample.title[:60])
