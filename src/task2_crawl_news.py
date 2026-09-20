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
    "https://baochinhphu.vn/quy-dinh-moi-nhat-ve-dao-tao-lai-xe-102250709174518501.htm",
    "https://baochinhphu.vn/cap-giay-phep-lai-xe-cho-nguoi-dat-ket-qua-sat-hach-trong-thoi-han-07-ngay-lam-viec-102250304091552224.htm",
    "https://baochinhphu.vn/bao-dam-trat-tu-an-toan-giao-thong-doi-voi-hoat-dong-kinh-doanh-van-tai-bang-xe-o-to-102260821114408935.htm",
    "https://baochinhphu.vn/tu-15-8-phat-canh-cao-o-to-cho-tre-em-duoi-10-tuoi-khong-co-thiet-bi-an-toan-phu-hop-102260630121104271.htm",
    "https://baochinhphu.vn/sua-doi-bo-sung-mot-so-quy-dinh-ve-trat-tu-an-toan-giao-thong-duong-bo-102260629181414298.htm",
]


def repair_mojibake(value: str) -> str:
    """Repair UTF-8 text that was decoded as Windows-1252."""
    try:
        repaired = value.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    broken_markers = ("Ã", "Ä", "Æ", "áº", "á»")
    if sum(repaired.count(marker) for marker in broken_markers) < sum(
        value.count(marker) for marker in broken_markers
    ):
        return repaired
    return value


async def crawl_article(url: str) -> dict:
    from datetime import datetime
    from crawl4ai import AsyncWebCrawler

    clean_url = url.split("?")[0]
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=clean_url)
        title = result.metadata.get("title", "").strip() or clean_url.split("/")[-1]
        return {
            "url": clean_url,
            "title": repair_mojibake(title),
            "date_crawled": datetime.now().isoformat(),
            "content_markdown": repair_mojibake(result.markdown or ""),
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
