"""Unified corpus ingestion CLI."""

from __future__ import annotations

import argparse
import asyncio

from .article_pipeline import process_articles
from .legal_pdf_pipeline import load_registry, process_pdf


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Etomidate citation-ready data pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--download", action="store_true"); group.add_argument("--pdf", action="store_true"); group.add_argument("--articles", action="store_true"); group.add_argument("--all", action="store_true")
    parser.add_argument("--source-id"); parser.add_argument("--max-pages", type=int); parser.add_argument("--skip-ocr", action="store_true"); parser.add_argument("--skip-gemini", action="store_true"); parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.download or args.all:
        from .task1_collect_legal_docs import download_documents, setup_directory
        setup_directory(); download_documents()
    registry = load_registry()
    if args.pdf or args.all:
        sources = [args.source_id] if args.source_id else [k for k,v in registry.items() if v.get("source_type") == "legal"]
        for sid in sources: process_pdf(sid, max_pages=args.max_pages, skip_ocr=args.skip_ocr, skip_gemini=args.skip_gemini, force=args.force)
    if args.articles or args.all:
        process_articles(source_id=args.source_id if args.source_id and registry[args.source_id].get("source_type") != "legal" else None, skip_gemini=args.skip_gemini, force=args.force)


if __name__ == "__main__": main()
