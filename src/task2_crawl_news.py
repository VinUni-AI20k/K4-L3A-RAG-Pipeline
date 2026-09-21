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
    "https://sme.misa.vn/349869/thue-thu-nhap-doanh-nghiep/",
    "https://sme.misa.vn/349941/chi-phi-khong-duoc-tru-khi-tinh-thue-tndn/",
    "https://www.meinvoice.vn/tin-tuc/14827/cac-loai-thue-doanh-nghiep-phai-nop/",
    "https://www.meinvoice.vn/tin-tuc/13508/xu-ly-hoa-don-dien-tu-co-sai-sot/",
    "https://www.meinvoice.vn/tin-tuc/18021/tong-hop-cac-quy-dinh-ve-hoa-don-dien-tu-khoi-tao-tu-may-tinh-tien/",
    "https://sme.misa.vn/215483/nhung-truong-hop-khong-duoc-khau-tru-thue-gia-tri-gia-tang-ke-toan-can-biet/",
]


async def crawl_article(url: str) -> dict:
    """Crawl bài viết bằng Crawl4AI, có fallback dự phòng nếu cần."""
    from datetime import datetime
    import re
    from crawl4ai import AsyncWebCrawler

    title = ""
    markdown_content = ""

    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            if result.success:
                markdown_content = result.markdown or ""
                metadata = result.metadata or {}
                title = metadata.get("title") or ""
    except Exception as exc:
        print(f"crawl4ai error for {url}: {exc}")

    # Fallback dự phòng nếu markdown hoặc title còn thiếu
    if not markdown_content or len(markdown_content.strip()) < 200 or not title:
        import requests
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        if not title:
            title_match = re.search(r"<title>(.*?)</title>", resp.text, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else "Bài viết Thuế Doanh nghiệp"
            # Cắt bỏ đuôi thương hiệu nếu có
            title = re.sub(r"\s*[\|\-–]\s*(MISA|meInvoice).*$", "", title).strip()
        if not markdown_content or len(markdown_content.strip()) < 200:
            # Loại bỏ script, style và trích xuất text
            cleaned = re.sub(r"<script.*?</script>", "", resp.text, flags=re.DOTALL | re.IGNORECASE)
            cleaned = re.sub(r"<style.*?</style>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
            cleaned = re.sub(r"<[^>]+>", " ", cleaned)
            markdown_content = "\n\n".join([line.strip() for line in cleaned.splitlines() if len(line.strip()) > 30])

    if not title:
        title = "Hướng dẫn nghiệp vụ Thuế Doanh nghiệp"

    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now().isoformat(),
        "content_markdown": markdown_content.strip(),
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
