import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src import task1_collect_legal_docs, task2_crawl_news, task3_convert_markdown



def test_legal_refresh_is_atomic_and_removes_stale_files(tmp_path):
    valid_pdf = b"%PDF" + b"x" * 2048

    class Response:
        content = valid_pdf

        @staticmethod
        def raise_for_status():
            pass

    stale = tmp_path / "old-policy.pdf"
    stale.write_bytes(valid_pdf)
    sources = {"current.pdf": {"title": "Current", "url": "https://example.test/current.pdf"}}
    with (
        patch.object(task1_collect_legal_docs, "DATA_DIR", tmp_path),
        patch.object(task1_collect_legal_docs, "LEGAL_SOURCES", sources),
        patch.object(task1_collect_legal_docs.requests, "get", return_value=Response()),
    ):
        task1_collect_legal_docs.download_documents()

    assert (tmp_path / "current.pdf").read_bytes() == valid_pdf
    assert not stale.exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_clean_markdown_normalizes_fragments_and_removes_personal_contacts():
    dirty = """menu
# Title
Ngày **10****/****08****/202****6**, **Nội****dung** chính.
Liên hệ Nguyễn Văn A: person@hust.edu.vn


Footer
Bản quyền thuộc HUST
"""
    cleaned = task2_crawl_news.clean_markdown(dirty)
    assert "**10/08/2026**" in cleaned
    assert "**Nội dung**" in cleaned
    assert "person@hust.edu.vn" not in cleaned
    assert "menu" not in cleaned
    assert "Bản quyền" not in cleaned

def test_refresh_removes_stale_files():
    with TemporaryDirectory() as temp:
        root = Path(temp)
        news_dir = root / "landing" / "news"
        news_dir.mkdir(parents=True)
        stale_json = news_dir / "failed.json"
        stale_json.write_text("stale", encoding="utf-8")
        sources = {
            f"item-{index}": {"title": f"Item {index}", "url": f"https://example.test/{index}"}
            for index in range(5)
        } | {"failed": {"title": "Failed", "url": "failed-url"}}

        async def failed_crawl(_url):
            raise RuntimeError("offline")

        with (
            patch.object(task2_crawl_news, "DATA_DIR", news_dir),
            patch.object(task2_crawl_news, "ARTICLE_SOURCES", sources),
            patch.object(task2_crawl_news, "crawl_article", failed_crawl),
        ):
            try:
                asyncio.run(task2_crawl_news.crawl_all())
            except RuntimeError:
                pass
            else:
                raise AssertionError("Crawl below the minimum should fail")
        assert stale_json.exists()

        async def fake_crawl(url):
            if url == "failed-url":
                raise RuntimeError("offline")
            return {
                "url": url,
                "title": url,
                "date_crawled": "2026-09-20T00:00:00+00:00",
                "content_markdown": "content " * 30,
            }

        with (
            patch.object(task2_crawl_news, "DATA_DIR", news_dir),
            patch.object(task2_crawl_news, "ARTICLE_SOURCES", sources),
            patch.object(task2_crawl_news, "crawl_article", fake_crawl),
        ):
            asyncio.run(task2_crawl_news.crawl_all())
        assert not stale_json.exists()

        standardized = root / "standardized" / "news"
        standardized.mkdir(parents=True)
        stale_markdown = standardized / "removed.md"
        stale_markdown.write_text("stale", encoding="utf-8")
        with (
            patch.object(task3_convert_markdown, "LANDING_DIR", root / "landing"),
            patch.object(task3_convert_markdown, "OUTPUT_DIR", root / "standardized"),
        ):
            task3_convert_markdown.convert_news_articles()
        assert not stale_markdown.exists()
        assert len(list(standardized.glob("*.md"))) == 5
