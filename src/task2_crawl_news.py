"""
Task 2 — Crawl bài viết/thông báo (chủ đề: Du lịch).

1. Điền 5 URL công khai về tin du lịch Việt Nam vào ARTICLE_URLS.
2. Ưu tiên dùng Crawl4AI nếu đã cài (cần: python -m playwright install chromium);
   nếu chưa cài, dùng fallback requests + extractor nội bộ để vẫn crawl được.
3. Lưu mỗi bài thành một JSON trong data/landing/news/.
4. Giữ đủ url, title, date_crawled và content_markdown.
"""

import asyncio
import json
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    # 8 tháng đầu năm: khách quốc tế đạt 15,9 triệu lượt người
    ("nhandan.vn", "https://nhandan.vn/8-thang-qua-khach-quoc-te-den-viet-nam-dat-159-trieu-luot-nguoi-post986169.html"),
    # Du lịch Việt Nam đạt 56% mục tiêu đón khách quốc tế năm 2026
    ("nhandan.vn", "https://nhandan.vn/du-lich-viet-nam-dat-56-muc-tieu-don-khach-quoc-te-nam-2026-post980076.html"),
    # Lượng du khách Nga đến Việt Nam dự báo cao kỷ lục trong năm 2026
    ("nhandan.vn", "https://nhandan.vn/luong-du-khach-nga-den-viet-nam-du-bao-cao-ky-luc-trong-nam-2026-post988386.html"),
    # Việt Nam nằm trong top 3 điểm đến châu Á có tỷ lệ du khách quay lại cao nhất
    ("nhandan.vn", "https://nhandan.vn/viet-nam-nam-trong-top-3-diem-den-chau-a-co-ty-le-du-khach-quay-lai-cao-nhat-post987462.html"),
    # Ngành du lịch hoàn thành gần 50% mục tiêu đón khách quốc tế trong năm 2026
    ("baochinhphu.vn", "https://baochinhphu.vn/nganh-du-lich-hoan-thanh-gan-50-muc-tieu-don-khach-quoc-te-trong-nam-2026-102260704145424103.htm"),
]

TIMEOUT = 30
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


class _NewsExtractor(HTMLParser):
    """Trích title + nội dung chính của bài báo về dạng markdown."""

    _SKIP_TAGS = {"script", "style", "noscript", "header", "footer", "nav", "aside", "form", "iframe"}
    _SKIP_CLASS = ("nav", "menu", "header", "footer", "sidebar", "related", "breadcrumb", "comment")
    _BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "li", "tr", "blockquote"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        classes = " ".join(value for _, value in attrs if _ == "class").lower()
        if tag in self._SKIP_TAGS or any(name in classes for name in self._SKIP_CLASS):
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in {"h1", "h2"}:
            self._parts.append("\n\n# ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS or tag in {"p", "li", "h1", "h2"} and self._skip_depth:
            if self._skip_depth:
                self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in {"p", "li", "h1", "h2"}:
            self._parts.append("\n\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title = (self.title + data).strip() if hasattr(self, "title") else data.strip()
        if not self._skip_depth:
            self._parts.append(data)

    def markdown(self) -> str:
        raw = "".join(self._parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n[ \t]+", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def fetch_and_extract(url: str) -> dict:
    """Fallback đọc bài bằng requests và trích nội dung markdown."""
    import requests

    response = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    parser = _NewsExtractor()
    parser.feed(response.text)
    markdown = parser.markdown()
    if len(markdown) < 200:
        raise RuntimeError(f"nội dung bài quá ngắn ({len(markdown)} ký tự)")
    return {
        "url": url,
        "title": getattr(parser, "title", "Unknown"),
        "date_crawled": datetime.now().isoformat(),
        "content_markdown": markdown,
    }


async def crawl_article(url: str) -> dict:
    """Crawl một bài và trả dict đúng schema news JSON."""
    try:
        import crawl4ai  # noqa: F401  (chưa cài -> dùng fallback)
    except ImportError:
        return await asyncio.to_thread(fetch_and_extract, url)

    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        return {
            "url": url,
            "title": (result.metadata or {}).get("title", "Unknown"),
            "date_crawled": datetime.now().isoformat(),
            "content_markdown": result.markdown or "",
        }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for index, (_, url) in enumerate(ARTICLE_URLS, 1):
        output = DATA_DIR / f"article_{index:02d}.json"
        if output.exists():
            print(f"Skipped (already exists): {output}")
            continue
        try:
            article = await crawl_article(url)
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved: {output}")
        except Exception as error:  # noqa: BLE001 - crawl lỗi 1 bài không dừng cả lô
            print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())