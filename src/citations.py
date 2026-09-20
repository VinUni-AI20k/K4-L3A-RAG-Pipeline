"""Citation rendering and post-generation validation."""

from __future__ import annotations

from datetime import datetime
import re


def format_article_citation(metadata: dict) -> str:
    publisher = metadata.get("publisher") or metadata.get("source") or "Nguồn"
    title = metadata.get("title") or "Không rõ tiêu đề"
    date = metadata.get("published_date")
    if date:
        try:
            date = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            pass
    author = metadata.get("author")
    parts = [publisher]
    if author:
        parts.append(author)
    parts.append(f'“{title}”')
    if date:
        parts.append(date)
    return " — ".join(parts)


def format_citation(metadata: dict) -> str:
    if metadata.get("doc_type") == "news" or metadata.get("source_type") in {
        "official_news", "trusted_news"
    }:
        return format_article_citation(metadata)
    document = metadata.get("document_title") or metadata.get("title") or "Văn bản"
    labels = []
    for key, label in (("article_number", "Điều"), ("clause_number", "Khoản"), ("point_number", "Điểm")):
        if metadata.get(key):
            labels.append(f"{label} {metadata[key]}")
    start, end = metadata.get("page_start"), metadata.get("page_end")
    page = None
    if start:
        page = f"Trang {start}" if not end or end == start else f"Trang {start}–{end}"
    return " — ".join(part for part in (document, ", ".join(labels), page) if part)


def extract_citation_ids(answer: str) -> list[str]:
    return re.findall(r"\[(E\d+)\]", answer)


def validate_citations(answer: str, evidence: list[dict]) -> dict:
    allowed = {f"E{i}" for i in range(1, len(evidence) + 1)}
    used = extract_citation_ids(answer)
    invalid = sorted(set(used) - allowed)
    warnings = []
    if answer.strip() and not used and len(answer.split()) >= 8:
        warnings.append("Answer contains a material statement without an evidence citation")
    return {"valid": not invalid, "citation_ids": used, "invalid_ids": invalid, "warnings": warnings}
