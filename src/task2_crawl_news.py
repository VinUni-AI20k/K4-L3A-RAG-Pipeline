"""
Task 2 — Crawl bài viết/thông báo.

Chủ đề nhóm: Luật giao thông đường bộ Việt Nam.
Nguồn: baochinhphu.vn — báo điện tử Chính phủ, cho phép crawler đọc bài.

Cài browser trước khi chạy:
    python -m playwright install chromium

Chạy lại nhiều lần vẫn ra đúng 5 file article_01..05.json (tên file cố định
theo vị trí trong ARTICLE_URLS) nên không sinh thêm bản sao.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

# Chỉ lấy tiêu đề, sapo và thân bài của baochinhphu.vn. Nếu crawl cả trang thì
# menu, banner và footer chiếm phần lớn Markdown, chunk sẽ toàn link điều hướng
# và retrieval mất độ chính xác.
ARTICLE_SELECTORS = [".detail-title", ".detail-sapo", ".detail-content"]

# Bỏ tham số tracking (utm_*) để URL lưu lại đúng bản công khai của bài viết.
ARTICLE_URLS = [
    "https://baochinhphu.vn/quy-dinh-moi-nhat-ve-dao-tao-lai-xe-102250709174518501.htm",
    "https://baochinhphu.vn/cap-giay-phep-lai-xe-cho-nguoi-dat-ket-qua-ky-sat-hach-trong-thoi-han-7-ngay-lam-viec-102250304091552224.htm",
    "https://baochinhphu.vn/bao-dam-trat-tu-an-toan-giao-thong-doi-voi-hoat-dong-kinh-doanh-van-tai-bang-xe-o-to-102260821114408935.htm",
    "https://baochinhphu.vn/tu-15-8-phat-canh-cao-o-to-cho-tre-em-khong-co-thiet-bi-an-toan-phu-hop-102260630121104271.htm",
    "https://baochinhphu.vn/sua-doi-bo-sung-mot-so-quy-dinh-ve-trat-tu-an-toan-giao-thong-duong-bo-102260629181414298.htm",
]

# Bài quá ngắn thường là trang lỗi hoặc bị chặn, không đưa vào corpus.
MIN_CONTENT_CHARS = 500


def extract_markdown(result) -> str:
    """Lấy Markdown từ CrawlResult (crawl4ai trả object hoặc str tuỳ version)."""
    markdown = result.markdown
    return getattr(markdown, "raw_markdown", None) or str(markdown)


async def crawl_article(url: str, crawler: AsyncWebCrawler | None = None) -> dict:
    """Crawl một bài viết và trả về dict đủ metadata bắt buộc."""
    if crawler is None:
        async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as own_crawler:
            return await crawl_article(url, own_crawler)

    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=60_000,
            target_elements=ARTICLE_SELECTORS,
            excluded_tags=["nav", "footer", "aside", "script", "style", "form"],
            markdown_generator=DefaultMarkdownGenerator(
                options={"ignore_links": True, "ignore_images": True, "body_width": 0}
            ),
        ),
    )
    if not result.success:
        raise RuntimeError(result.error_message or "crawl failed")

    content = extract_markdown(result).strip()
    if len(content) < MIN_CONTENT_CHARS:
        raise RuntimeError(f"nội dung quá ngắn ({len(content)} ký tự), có thể bị chặn")

    metadata = result.metadata or {}
    return {
        "url": url,
        "title": (metadata.get("title") or "").strip() or url,
        "date_crawled": datetime.now().isoformat(timespec="seconds"),
        "content_markdown": content,
        "date_published": (metadata.get("article:published_time") or "").strip(),
        "description": (metadata.get("description") or "").strip(),
    }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    saved = 0
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        for index, url in enumerate(ARTICLE_URLS, 1):
            try:
                article = await crawl_article(url, crawler)
                output = DATA_DIR / f"article_{index:02d}.json"
                output.write_text(
                    json.dumps(article, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                saved += 1
                print(f"Saved: {output.name} ({len(article['content_markdown'])} ký tự)")
            except Exception as error:
                print(f"Failed: {url} — {error}")

    print(f"Crawled {saved}/{len(ARTICLE_URLS)} bài viết vào {DATA_DIR}")


if __name__ == "__main__":
    # Console Windows mặc định là cp1252 nên print tiếng Việt sẽ crash.
    if (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    asyncio.run(crawl_all())
