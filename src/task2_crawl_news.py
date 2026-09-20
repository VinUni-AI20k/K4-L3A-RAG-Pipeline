"""
Task 2 — Thu thập năm trang tham khảo công khai về Vật lí 10–12.

Hướng dẫn:
    1. Dùng năm trang bách khoa cùng chủ đề với ba sách giáo khoa.
    2. Lấy nội dung qua MediaWiki API để giữ văn bản sạch và URL gốc.
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Văn bản Wikipedia có giấy phép CC BY-SA; URL và giấy phép được ghi trong JSON.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import requests


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_TITLES = [
    "Động năng",                 # Vật lí 10
    "Dao động điều hòa",         # Vật lí 11
    "Điện trường",               # Vật lí 11
    "Nhiệt động lực học",        # Vật lí 12
    "Từ trường",                  # Vật lí 12
]
ARTICLE_URLS = [
    f"https://vi.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
    for title in ARTICLE_TITLES
]
API_URL = "https://vi.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "K4-RAG-Lab/0.1 (educational corpus collection)"}


async def crawl_article(url: str) -> dict:
    """Lấy một trang Wikipedia tiếng Việt và giữ thông tin nguồn."""
    if url not in ARTICLE_URLS:
        raise ValueError(f"URL không nằm trong danh sách nguồn đã chọn: {url}")
    title = unquote(urlsplit(url).path.rsplit("/", 1)[-1]).replace("_", " ")
    response = await asyncio.to_thread(
        requests.get,
        API_URL,
        params={
            "action": "query",
            "prop": "info|extracts",
            "inprop": "url",
            "explaintext": 1,
            "exintro": 1,
            "format": "json",
            "titles": title,
        },
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    pages = response.json()["query"]["pages"]
    page = next(iter(pages.values()))
    content = page.get("extract", "").strip()
    if "missing" in page or len(content) < 200:
        raise ValueError(f"Trang không tồn tại hoặc quá ngắn: {url}")
    return {
        "url": page["fullurl"],
        "title": page["title"],
        "date_crawled": datetime.now(timezone.utc).isoformat(),
        "content_markdown": f"# {page['title']}\n\n{content}",
        "content_scope": "Phần mở đầu của bài viết công khai",
        "license": "CC BY-SA; xem giấy phép và lịch sử tác giả tại URL nguồn",
    }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    failures = []
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
            failures.append(url)

    if failures:
        raise RuntimeError(f"Không thu thập được {len(failures)} trong 5 trang")


if __name__ == "__main__":
    asyncio.run(crawl_all())
