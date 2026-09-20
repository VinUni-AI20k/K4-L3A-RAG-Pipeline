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
    "https://www.vnulib.edu.vn/index.php/muon-tra-tai-lieu-tvtt",
    "https://vnulib.edu.vn/index.php/cau-hoi-thuong-gap-tai-tvtt",
    "https://vnulib.edu.vn/index.php/general/36-dich-vu-thu-vien/147-tap-huan-tv",
    "https://vnulib.edu.vn/index.php/general/36-dich-vu-thu-vien/146-cung-cap-thong-tin-theo-yeu-cau-tvtt",
    "https://vnulib.edu.vn/index.php/general/9-tin-tuc-su-kien-thong-bao/428-tb-dieu-chinh-muon-tra-tl-2026",
    "https://vnulib.edu.vn/index.php/2014-05-22-10-14-38",
    "https://vnulib.edu.vn/index.php/dang-ky-lam-the-thu-vien",
]


async def crawl_article(url: str) -> dict:
    from datetime import datetime

    from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig

    # vnulib.edu.vn (Joomla) đặt nội dung bài trong div.item-page; lấy riêng
    # phần này để markdown không lẫn logo, menu, sidebar và bản đồ.
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        target_elements=[".item-page"],  # không dùng css_selector: nó làm mất <title>
        excluded_tags=["nav", "header", "footer", "aside", "form", "script", "style"],
        remove_overlay_elements=True,
    )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=config)
        if not result.success:
            raise RuntimeError(result.error_message or "crawl failed")
        content = str(result.markdown or "").strip()
        if not content:
            raise RuntimeError("empty content")
        return {
            "url": url,
            "title": (result.metadata or {}).get("title") or "Unknown",
            "date_crawled": datetime.now().isoformat(),
            "content_markdown": content,
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
