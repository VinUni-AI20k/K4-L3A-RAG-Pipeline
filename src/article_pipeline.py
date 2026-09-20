"""Structure and standardize raw article records without losing provenance."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re

from pydantic import BaseModel, Field, HttpUrl

from .legal_pdf_pipeline import DATA, GeminiStructurer, SCHEMA_VERSION, STRUCTURING_MODEL, load_registry


class ArticleRecord(BaseModel):
    source_id: str
    title: str
    publisher: str | None = None
    author: str | None = None
    published_date: str | None = None
    updated_date: str | None = None
    url: str
    canonical_url: str
    source_type: str
    trust_level: str
    topics: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    content: str
    content_sha256: str
    input_content_sha256: str | None = None
    structuring_model: str
    schema_version: str = SCHEMA_VERSION


ARTICLE_INSTRUCTION = "Preserve factual wording. Never summarize or add facts. Remove only navigation, footer, duplicate headings and unrelated links. If uncertain, return null."


def content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def offline_article(raw: dict, registry: dict) -> ArticleRecord:
    content = str(raw.get("content_markdown") or raw.get("content") or "").strip()
    return ArticleRecord(
        source_id=registry["source_id"], title=raw.get("title") or registry.get("title") or registry["source_id"],
        publisher=raw.get("publisher") or registry.get("publisher"), author=raw.get("author"),
        published_date=raw.get("published_date") or registry.get("published_date"), updated_date=raw.get("updated_date"),
        url=raw.get("url") or registry["url"], canonical_url=raw.get("canonical_url") or raw.get("url") or registry["url"],
        source_type=registry["source_type"], trust_level=registry["trust_level"], topics=[], entities=[], content=content,
        content_sha256=raw.get("content_sha256") or content_sha256(content), structuring_model="rule-based-offline",
        input_content_sha256=raw.get("content_sha256") or content_sha256(content),
    )


def validate_article(record: ArticleRecord) -> None:
    if not all((record.source_id.strip(), record.title.strip(), (record.publisher or "").strip(), record.content.strip())):
        raise ValueError("Article requires source_id, title, publisher and content")
    if not re.match(r"https?://", record.url): raise ValueError("Article URL must be HTTP(S)")
    if record.content_sha256 != content_sha256(record.content): raise ValueError("Article content SHA256 mismatch")


def process_articles(*, source_id: str | None = None, skip_gemini: bool = False, force: bool = False) -> tuple[list[dict], int]:
    registry = load_registry(); selected = [source_id] if source_id else [k for k,v in registry.items() if v.get("source_type") != "legal"]
    structured = DATA / "structured" / "news"; standardized = DATA / "standardized" / "news"; errors_path = DATA / "errors.jsonl"
    structured.mkdir(parents=True, exist_ok=True); standardized.mkdir(parents=True, exist_ok=True)
    output, seen_hashes, duplicates = [], set(), 0
    for sid in selected:
        try:
            raw_path = DATA / "landing" / "news" / f"{sid}.json"; raw = json.loads(raw_path.read_text(encoding="utf-8"))
            existing_path = structured / f"{sid}.json"
            raw_hash = raw.get("content_sha256") or content_sha256(str(raw.get("content_markdown") or "").strip())
            if not force and existing_path.exists():
                existing = ArticleRecord.model_validate_json(existing_path.read_text(encoding="utf-8"))
                if existing.input_content_sha256 == raw_hash and existing.structuring_model == ("rule-based-offline" if skip_gemini else STRUCTURING_MODEL):
                    if existing.content_sha256 in seen_hashes: duplicates += 1; continue
                    seen_hashes.add(existing.content_sha256); output.append(existing.model_dump()); print(f"[CACHE] {sid} hit"); continue
            record = offline_article(raw, registry[sid])
            if not skip_gemini:
                prompt = f"{ARTICLE_INSTRUCTION}\nRegistry: {json.dumps(registry[sid], ensure_ascii=False)}\nRaw article:\n{record.content}"
                record = GeminiStructurer().structured(prompt, ArticleRecord)
                record.content_sha256 = content_sha256(record.content); record.input_content_sha256 = raw_hash; record.structuring_model = STRUCTURING_MODEL
            validate_article(record)
            if record.content_sha256 in seen_hashes: duplicates += 1; print(f"[DEDUP] {sid}"); continue
            seen_hashes.add(record.content_sha256); item = record.model_dump(); output.append(item)
            (structured / f"{sid}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
            (standardized / f"{sid}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
            md = f"---\nsource_id: {sid}\ntitle: {record.title}\npublisher: {record.publisher}\npublished_date: {record.published_date}\nurl: {record.canonical_url}\ntrust_level: {record.trust_level}\nsource_type: {record.source_type}\n---\n\n# {record.title}\n\n{record.content}\n"
            (standardized / f"{sid}.md").write_text(md, encoding="utf-8"); print(f"[SAVED] {sid}")
        except Exception as exc:
            error = {"source_id": sid, "stage": "article_structuring", "url": registry[sid].get("url"), "error": str(exc)}
            with errors_path.open("a", encoding="utf-8") as stream: stream.write(json.dumps(error, ensure_ascii=False) + "\n")
            print(f"[ERROR] {sid}: {exc}")
    return output, duplicates
