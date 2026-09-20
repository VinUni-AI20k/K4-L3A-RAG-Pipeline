"""
Task 2 — Crawl bài viết/thông báo.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng Crawl4AI.
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Cài browser trước khi chạy:
    python -m playwright install chromium
    
-> Dùng Firecrawl or bất cứ công cụ nào bạn quen    
"""

import asyncio
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://daotao.ueh.edu.vn/thong-bao-ve-viec-nop-ho-so-de-nghi-mien-giam-hoc-phi-va-ho-tro-chi-phi-hoc-tap-trong-hkd-nam-2026-doi-voi-sinh-vien-dhcq-lien-thong-dhcq/",
    "https://daotao.ueh.edu.vn/thong-bao-danh-sach-sinh-vien-duoc-xet-duyet-mien-giam-hoc-phi-dot-2-hoc-ky-cuoi-nam-2026/",
    "https://dsa.ueh.edu.vn/tin-tuc/thong-bao-ve-viec-thu-noi-tru-phi-ky-tuc-xa-quy-iii-2026-thang-789-nam-2026/",
    "https://dsa.ueh.edu.vn/tin-tuc/kh-xet-hb-ueh-2026/",
    "https://nhaphoc.ueh.edu.vn/dinh-huong-sau-nhap-hoc/ho-tro-va-cham-soc/cham-soc-suc-khoe/",
]


class _ArticleParser(HTMLParser):
    """Trích xuất văn bản đọc được từ HTML mà không cần browser automation."""

    CONTENT_TAGS = {"h1", "h2", "h3", "p", "li", "td"}
    SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header"}

    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self._active_tag: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if self._skip_depth == 0 and tag in self.CONTENT_TAGS:
            self._active_tag = tag

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if self._skip_depth == 0 and tag == self._active_tag:
            self._active_tag = None
        if tag in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        if self._in_title:
            self.title += f" {text}"
        if self._skip_depth == 0 and self._active_tag:
            prefix = "# " if self._active_tag == "h1" else "## " if self._active_tag in {"h2", "h3"} else "- " if self._active_tag == "li" else ""
            self._parts.append(f"{prefix}{text}")

    @property
    def markdown(self) -> str:
        return "\n\n".join(dict.fromkeys(self._parts)).strip()


async def crawl_article(url: str) -> dict:
    def fetch() -> dict:
        response = requests.get(
            url,
            headers={"User-Agent": "K4-RAG-Lab/1.0 (educational project)"},
            timeout=45,
        )
        response.raise_for_status()
        parser = _ArticleParser()
        parser.feed(response.text)
        title = re.sub(r"\s+", " ", parser.title).strip() or "Untitled article"
        content = parser.markdown
        if len(content) < 200:
            raise ValueError("Extracted article content is too short")
        return {
            "url": url,
            "title": title,
            "date_crawled": datetime.now(timezone.utc).isoformat(),
            "content_markdown": content,
        }

    return await asyncio.to_thread(fetch)


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for index, url in enumerate(ARTICLE_URLS, 1):
        try:
            article = await crawl_article(url)
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved: {output}")
        except Exception as error:
            print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
