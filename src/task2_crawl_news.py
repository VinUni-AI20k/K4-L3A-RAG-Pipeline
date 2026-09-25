"""
Task 2 — Crawl bài viết/thông báo.

Nguồn: các bài hướng dẫn/FAQ công khai trên Trung tâm trợ giúp Shopee
(help.shopee.vn) liên quan tới trả hàng, hoàn tiền và vận chuyển — bổ sung cho
các tài liệu chính sách ở Task 1.

help.shopee.vn render bằng JavaScript nên cần trình duyệt headless (Crawl4AI +
Playwright). Cài browser trước khi chạy:
    python -m playwright install chromium
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    # [Trả hàng/Hoàn tiền] Thời gian nhận tiền hoàn và cách kiểm tra tiền hoàn
    "https://help.shopee.vn/portal/4/article/79507",
    # [Trả hàng/Hoàn tiền] Các phương thức gửi hàng hoàn trả và phí hoàn trả
    "https://help.shopee.vn/portal/4/article/79061",
    # [Hoàn tiền] Không nhận được tiền hoàn cho đơn thanh toán qua Ví ShopeePay
    "https://help.shopee.vn/portal/4/article/79548",
    # [Trả hàng/Hoàn tiền] Kiểm tra tiền đã hoàn vào SPayLater
    "https://help.shopee.vn/portal/4/article/164831",
    # Hướng dẫn liên quan tới yêu cầu trả hàng
    "https://help.shopee.vn/portal/4/article/79508",
    # Các đơn vị vận chuyển trên Shopee
    "https://help.shopee.vn/portal/4/article/79088",
    # Điều Khoản Dịch Vụ của Shopee Mall (gồm chính sách trả hàng Shopee Mall)
    "https://help.shopee.vn/portal/4/article/77262",
]

TITLE_SUFFIX = " | Shopee Trung tâm trợ giúp"


def extract_article(markdown: str, title: str) -> str:
    """Bỏ menu điều hướng phía trên tiêu đề bài viết và widget đánh giá phía dưới."""
    lines = markdown.splitlines()
    start = 0
    # Tiêu đề bài là heading đầu tiên khớp với <title> của trang.
    for index, line in enumerate(lines):
        heading = re.match(r"^#{1,3}\s+(.*)", line)
        if heading and heading.group(1).strip().lower() == title.strip().lower():
            start = index
            break
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].strip().startswith("Bạn có hài lòng với bài viết này"):
            end = index
            break
    return "\n".join(lines[start:end]).strip()


async def crawl_article(url: str, crawler=None) -> dict:
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

    config = CrawlerRunConfig(
        wait_until="networkidle",
        page_timeout=60_000,
        delay_before_return_html=3,
    )
    if crawler is None:
        async with AsyncWebCrawler() as own_crawler:
            return await crawl_article(url, own_crawler)

    result = await crawler.arun(url=url, config=config)
    if not result.success:
        raise RuntimeError(result.error_message or "crawl failed")
    title = (result.metadata or {}).get("title") or "Unknown"
    title = title.removesuffix(TITLE_SUFFIX).strip()
    content = extract_article(str(result.markdown), title)
    if len(content) < 200:
        raise RuntimeError(f"article body too short ({len(content)} chars)")
    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now().isoformat(timespec="seconds"),
        "content_markdown": content,
    }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    from crawl4ai import AsyncWebCrawler

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    async with AsyncWebCrawler() as crawler:
        for index, url in enumerate(ARTICLE_URLS, 1):
            try:
                article = await crawl_article(url, crawler)
                output = DATA_DIR / f"article_{index:02d}.json"
                output.write_text(
                    json.dumps(article, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"Saved: {output.name} — {article['title']}")
            except Exception as error:
                print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
