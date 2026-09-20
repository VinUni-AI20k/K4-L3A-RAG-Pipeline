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

from datetime import datetime
import asyncio
import json
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import markdownify


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://vnexpress.net/bi-quyet-chinh-phuc-band-7-ielts-writing-speaking-5053527.html",
    "https://vnexpress.net/the-ielts-workshop-gioi-thieu-mo-hinh-l-i-m-trong-hoc-tieng-anh-5121228.html",
    "https://vnexpress.net/anh-em-sinh-doi-cung-dat-9-0-ielts-5103526.html",
    "https://vnexpress.net/loi-the-xet-tuyen-dai-hoc-viet-nam-va-the-gioi-khi-co-sat-5052935.html",
    "https://vnexpress.net/dinh-dang-bai-thi-toefl-ibt-moi-co-gi-thay-doi-5075150.html",
]


async def crawl_article(url: str) -> dict:
    """Crawl một bài viết và trích xuất title, content sang markdown."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Chạy request trong thread pool để không block event loop
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None, lambda: requests.get(url, headers=headers, timeout=20)
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Tìm tiêu đề bài viết
    title_elem = (
        soup.find("h1", class_="title-detail")
        or soup.find("h1", class_="title-news")
        or soup.find("h1")
    )
    title = title_elem.get_text(strip=True) if title_elem else "Tiêu đề bài viết"

    # Tìm phần nội dung chính
    body_elem = (
        soup.find("article", class_="fck_detail")
        or soup.find("div", class_="fck_detail")
        or soup.find("article")
        or soup.find("main")
    )

    if body_elem:
        # Xóa các thành phần rác nếu có
        for tag in body_elem.find_all(["script", "style", "iframe", "figure"]):
            tag.decompose()
        content_markdown = markdownify.markdownify(str(body_elem), heading_style="ATX").strip()
    else:
        content_markdown = soup.get_text(separator="\n\n", strip=True)

    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now().isoformat(),
        "content_markdown": content_markdown,
    }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for index, url in enumerate(ARTICLE_URLS, 1):
        try:
            print(f"Crawling ({index}/{len(ARTICLE_URLS)}): {url}")
            article = await crawl_article(url)
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved: {output} (Title: {article['title']})")
        except Exception as error:
            print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
