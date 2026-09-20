"""
Task 2 — Crawl bài viết/thông báo du lịch.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng Crawl4AI (hoặc fallback request).
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
import re

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://vnexpress.net/cam-nang-du-lich-ha-giang-4445788.html",
    "https://vnexpress.net/cam-nang-du-lich-da-nang-4470111.html",
    "https://vnexpress.net/cam-nang-du-lich-phu-quoc-4106697.html",
    "https://vnexpress.net/cam-nang-du-lich-ta-xua-4656282.html",
    "https://vnexpress.net/cam-nang-du-lich-nha-trang-tu-a-den-z-4127199.html",
]


async def crawl_article(url: str) -> dict:
    """Crawl bài viết bằng Crawl4AI, có fallback sang httpx + bs4 nếu browser lỗi."""
    date_crawled = datetime.now().isoformat()

    # Cách 1: Thử crawl bằng Crawl4AI theo chuẩn repo
    try:
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            if result.success and result.markdown:
                title = (
                    result.metadata.get("title")
                    or result.metadata.get("og:title")
                    or "Unknown Title"
                )
                return {
                    "url": url,
                    "title": title.strip(),
                    "date_crawled": date_crawled,
                    "content_markdown": result.markdown.strip(),
                }
    except Exception as crawl_err:
        print(f"[Crawl4AI Notice] Lỗi chạy browser ({crawl_err}), chuyển sang HTTP fallback...")

    # Cách 2: Fallback bằng HTTP request nếu Playwright chưa cấu hình xong
    import httpx
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Lấy tiêu đề bài viết
    title_tag = (
        soup.find("h1", class_="title-detail")
        or soup.find("h1")
        or soup.find("title")
    )
    title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

    # Lấy nội dung chính của bài viết
    article_body = (
        soup.find("article", class_="fck_detail")
        or soup.find("div", class_="fck_detail")
        or soup.find("article")
    )

    markdown_lines = []
    if article_body:
        for element in article_body.find_all(["h2", "h3", "p"]):
            text = element.get_text(strip=True)
            if not text:
                continue
            if element.name == "h2":
                markdown_lines.append(f"\n## {text}\n")
            elif element.name == "h3":
                markdown_lines.append(f"\n### {text}\n")
            else:
                markdown_lines.append(text)
        content_markdown = "\n\n".join(markdown_lines)
    else:
        # Dự phòng lấy text thuần nếu không tìm thấy tag cụ thể
        content_markdown = soup.get_text(separator="\n\n", strip=True)

    return {
        "url": url,
        "title": title,
        "date_crawled": date_crawled,
        "content_markdown": f"# {title}\n\n{content_markdown}",
    }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for index, url in enumerate(ARTICLE_URLS, 1):
        try:
            print(f"[{index}/{len(ARTICLE_URLS)}] Crawling: {url} ...")
            article = await crawl_article(url)
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f" -> Saved: {output.name} (Title: {article.get('title')[:40]}...)")
        except Exception as error:
            print(f" -> Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())