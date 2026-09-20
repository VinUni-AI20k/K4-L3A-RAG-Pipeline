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
    "https://tuoitre.vn/khong-su-dung-doanh-thu-nam-2026-de-xac-dinh-lai-nghia-vu-thue-cua-ho-kinh-doanh-20260306110116155.htm",
    "https://tuoitre.vn/sap-co-huong-dan-ke-khai-tinh-thue-su-dung-hoa-don-voi-ho-kinh-doanh-20260106110638208.htm",
    "https://vnexpress.net/co-quan-thue-huong-dan-ho-kinh-doanh-ke-khai-nop-thue-tu-2026-5013509.html",
    "https://tuoitre.vn/ho-kinh-doanh-co-doanh-thu-tren-500-trieu-dong-nam-moi-phai-nop-thue-20251219110854944.htm",
    "https://tuoitre.vn/ho-kinh-doanh-ca-nhan-kinh-doanh-se-bi-truy-thu-thue-nhung-nam-truoc-trong-truong-hop-nao-20260328122929988.htm",
    "https://vnexpress.net/nang-nguong-doanh-thu-chiu-thue-voi-ho-kinh-doanh-len-1-ty-dong-5068454.html",
]


async def crawl_article(url: str) -> dict:
    from datetime import datetime

    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        title = (result.metadata or {}).get("title") or url
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
