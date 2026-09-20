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
from datetime import datetime
import json
from pathlib import Path
from crawl4ai import AsyncWebCrawler


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

# TODO: Thêm ít nhất 5 public URL.
ARTICLE_URLS = [
    "https://ieltsliz.com/ielts-band-scores/",
    "https://ieltsliz.com/ielts-writing-task-1-lessons-and-tips/",
    "https://ieltsliz.com/ielts-writing-task-1-band-scores/",
    "https://ieltsliz.com/ielts-writing-task-2-band-scores-5-to-8/",
    "https://ieltsliz.com/ielts-sample-essay/",
    "https://ieltsliz.com/ielts-writing-task-2-discussion-essay-expressions/",
]


async def crawl_article(url: str) -> dict:
    # TODO: Implement crawling logic.
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        title = result.metadata.get("title", "")
        if not title:
            title = "IELTS Writing Guide"
        title = title.split(" - IELTS Liz")[0].split(" | IELTS Liz")[0].strip()

        return {
            "url": url,
            "title": title,
            "date_crawled": datetime.now().isoformat(),
            "content_markdown": result.markdown,
        }


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
