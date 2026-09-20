"""
Task 2 — Crawl bài viết/thông báo.

Chủ đề nhóm: IELTS Writing — band descriptors, tiêu chí chấm điểm, bài viết mẫu.

Nguồn được chọn gồm trang chính chủ (ielts.org, IDP IELTS) và các trang luyện thi
uy tín. Hai nguồn bị WAF chặn (British Council blog, global-english.com) đã được
loại bỏ thay vì tìm cách vượt.

Cài browser trước khi chạy:
    python -m playwright install chromium

Chạy:
    python -m src.task2_crawl_news
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    # Chính chủ: thông báo phát hành band descriptors + giải thích thang điểm.
    "https://ielts.org/news-and-insights/ielts-writing-band-descriptors-and-key-assessment-criteria",
    "https://ielts.idp.com/results/scores/writing",
    "https://ielts.idp.com/prepare/article-10-tips-improve-your-ielts-writing-band-score",
    # Trang luyện thi: diễn giải tiêu chí và bài mẫu theo band.
    "https://ieltsliz.com/ielts-writing-task-2-band-descriptors/",
    "https://www.ieltsadvantage.com/2023/01/15/ielts-writing-task-2-sample-essays/",
    "https://www.ieltsadvantage.com/writing-task-2/",
    "https://ted-ielts.com/band-9-sample-answers/",
    "https://ted-ielts.com/ielts-writing-task-2/",
    "https://ieltstutors.org/writing-band-descriptors/",
    "https://www.cathoven.com/blog/common-mistakes-in-ielts-writing-task-2/",
]

# Đã loại https://ieltsliz.com/ielts-sample-essay/ : ~90% nội dung là comment của
# học viên (tiếng Anh nhiều lỗi), sẽ làm nhiễu corpus và át index vì quá dài.

# Bỏ các khối điều hướng để markdown còn lại chủ yếu là nội dung bài.
RUN_CONFIG = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,
    excluded_tags=["nav", "header", "footer", "aside", "form", "script", "style"],
    exclude_external_links=True,
    remove_overlay_elements=True,
    word_count_threshold=10,
    page_timeout=60_000,
)

MIN_CONTENT_CHARS = 200


def slugify(url: str) -> str:
    """Đặt tên file không dấu, ổn định theo URL để chạy lại không sinh bản trùng."""
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "").split(".")[0]
    tail = parsed.path.strip("/").split("/")[-1] or "index"
    slug = re.sub(r"[^a-z0-9]+", "-", f"{host}-{tail}".lower()).strip("-")
    return slug[:80]


def _extract_markdown(result) -> str:
    """Crawl4AI trả object markdown; lấy raw_markdown nếu có."""
    markdown = getattr(result, "markdown", "") or ""
    return str(getattr(markdown, "raw_markdown", markdown)).strip()


async def crawl_article(url: str, crawler: AsyncWebCrawler | None = None) -> dict:
    """Crawl một URL và trả về dict đúng schema yêu cầu."""
    if crawler is None:
        async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as owned:
            return await crawl_article(url, owned)

    result = await crawler.arun(url=url, config=RUN_CONFIG)
    if not getattr(result, "success", False):
        raise RuntimeError(getattr(result, "error_message", "crawl failed"))

    content = _extract_markdown(result)
    if len(content) < MIN_CONTENT_CHARS:
        raise RuntimeError(f"nội dung quá ngắn ({len(content)} ký tự)")

    metadata = getattr(result, "metadata", None) or {}
    title = (metadata.get("title") or "").strip() or slugify(url)

    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now().isoformat(timespec="seconds"),
        "content_markdown": content,
    }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    failed: list[str] = []

    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        for url in ARTICLE_URLS:
            try:
                article = await crawl_article(url, crawler)
            except Exception as error:
                print(f"FAIL {url} — {error}")
                failed.append(url)
                continue

            output = DATA_DIR / f"{slugify(url)}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            saved.append(output.name)
            print(f"OK   {output.name} ({len(article['content_markdown']):,} ký tự)")

    print(f"\nĐã lưu {len(saved)}/{len(ARTICLE_URLS)} bài vào {DATA_DIR}")
    if failed:
        print(f"Thất bại: {len(failed)} — {', '.join(failed)}")
    if len(saved) < 5:
        raise RuntimeError("Cần tối thiểu 5 bài; hãy bổ sung hoặc thay URL.")


if __name__ == "__main__":
    asyncio.run(crawl_all())
