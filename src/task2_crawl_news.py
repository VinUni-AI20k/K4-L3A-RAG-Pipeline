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
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://ptit.edu.vn/thong-bao-cac-phuong-thuc-tuyen-sinh-dai-hoc-he-chinh-quy-nam-2026/",
    "https://ptit.edu.vn/hoc-vien-cong-nghe-buu-chinh-vien-thong-du-kien-tuyen-sinh-khoang-8-000-sinh-vien-nam-2026/",
    "https://khoahoc.vietjack.com/tuyen-sinh/1101/hoc-phi-truong-hoc-vien-cong-nghe-buu-chinh-vien-thong-nam-2026",
    "https://daibieunhandan.vn/print/10404779.html",
    "https://vnexpress.net/chi-tieu-nganh-hoc-hoc-phi-hoc-vien-cong-nghe-buu-chinh-vien-thong-ptit-nam-2026-5073150.html",
]


async def crawl_article(url: str) -> dict:
    from datetime import datetime
    from crawl4ai import AsyncWebCrawler

    print(f"Crawling: {url}...")
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        return {
            "url": url,
            "title": result.metadata.get("title", "Unknown") if result.metadata else "Unknown",
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
