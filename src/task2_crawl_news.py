"""
Task 2 — Crawl bài viết về du lịch Việt Nam.

Nguồn gồm hai nhóm: trang chính thức của Cục Du lịch Quốc gia và trang bách khoa
mở (Wikipedia/Wikivoyage) cho thông tin điểm đến, ẩm thực và hướng dẫn thực tế.

Cổng vietnamtourism.gov.vn là SPA: nội dung chỉ xuất hiện sau khi JavaScript chạy
xong, nên cần wait_until="networkidle" thay vì lấy HTML thô. Tên file theo slug của
URL để chạy lại không sinh bản sao.

Cài browser trước khi chạy:
    python -m playwright install chromium
"""

import asyncio
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

# Ngắn hơn ngưỡng này thì gần như chắc chắn JS chưa render xong.
MIN_CONTENT_CHARS = 1000

ARTICLE_URLS = [
    # Nguồn chính thức — Cục Du lịch Quốc gia Việt Nam
    "https://vietnamtourism.gov.vn/post/23086",
    "https://vietnamtourism.gov.vn/index.php/items/24281",
    # Bách khoa mở — điểm đến và ẩm thực
    "https://vi.wikipedia.org/wiki/Du_lịch_Việt_Nam",
    "https://vi.wikipedia.org/wiki/Vịnh_Hạ_Long",
    "https://vi.wikipedia.org/wiki/Phố_cổ_Hội_An",
    "https://vi.wikipedia.org/wiki/Sa_Pa",
    "https://vi.wikipedia.org/wiki/Ẩm_thực_Việt_Nam",
    # Hướng dẫn thực tế cho khách quốc tế (thị thực, đi lại, tiền tệ)
    "https://en.wikivoyage.org/wiki/Vietnam",
]


def slugify_url(url: str) -> str:
    """Đổi URL thành slug ASCII ổn định để đặt tên file."""
    path = re.sub(r"^https?://", "", url).rstrip("/")
    decoded = unicodedata.normalize("NFKD", path)
    ascii_only = decoded.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only).strip("-").lower()
    return slug[:80]


async def crawl_article(crawler: AsyncWebCrawler, url: str) -> dict:
    """Crawl một URL và trả về bản ghi theo schema của Task 2."""
    config = CrawlerRunConfig(
        wait_until="networkidle",
        delay_before_return_html=8.0,
        page_timeout=60000,
    )
    result = await crawler.arun(url=url, config=config)
    if not result.success:
        raise RuntimeError(result.error_message or "crawl failed")

    content = str(result.markdown or "")
    if len(content) < MIN_CONTENT_CHARS:
        raise RuntimeError(f"nội dung quá ngắn ({len(content)} ký tự)")

    metadata = result.metadata or {}
    title = metadata.get("title") or slugify_url(url).replace("-", " ").title()

    return {
        "url": url,
        "title": title.strip(),
        "date_crawled": datetime.now().isoformat(),
        "content_markdown": content,
    }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    saved = 0

    async with AsyncWebCrawler(verbose=False) as crawler:
        for url in ARTICLE_URLS:
            output = DATA_DIR / f"{slugify_url(url)}.json"
            if output.exists():
                print(f"Skip (đã có): {output.name}")
                saved += 1
                continue
            try:
                article = await crawl_article(crawler, url)
                output.write_text(
                    json.dumps(article, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                chars = len(article["content_markdown"])
                print(f"Saved: {output.name} ({chars:,} ký tự) — {article['title'][:50]}")
                saved += 1
            except Exception as error:
                print(f"Failed: {url} — {error}")

    print(f"\n{saved}/{len(ARTICLE_URLS)} bài viết trong {DATA_DIR}")
    if saved < 5:
        print("Cảnh báo: cần tối thiểu 5 bài để pass acceptance test.")


if __name__ == "__main__":
    asyncio.run(crawl_all())
