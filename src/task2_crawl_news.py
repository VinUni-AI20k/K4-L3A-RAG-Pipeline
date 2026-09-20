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
import re
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://www.vietnam.travel/vi/things-to-do/11-must-see-attractions-ha-noi",
    "https://vietnam.travel/vi/places-to-go/northern-vietnam/ha-long",
    "https://vietnam.travel/vi/things-to-do/10-essential-things-do-hoi-an",
    "https://vietnam.travel/vi/things-to-do/must-do-da-nang-an-insider-list",
    "https://vietnam.travel/vi/things-to-do/day-phu-quoc",
]


END_MARKERS = (
    "## xem thêm",
    "## thư viện ảnh",
    "#### đăng ký nhận bản tin",
    "#### **bạn muốn",
)


def clean_article_markdown(markdown: str, title: str) -> str:
    """Giữ nội dung bài chính và loại menu, footer, form của Vietnam Tourism."""
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    search_indexes = [
        index for index, line in enumerate(lines)
        if line.strip().casefold() == "tìm kiếm".casefold()
    ]
    search_start = search_indexes[-1] + 1 if search_indexes else 0

    heading_index = next(
        (
            index for index in range(search_start, len(lines))
            if re.match(r"^#{1,2}\s+\S", lines[index].strip())
        ),
        None,
    )
    if heading_index is None:
        raise ValueError(f"Không tìm thấy phần nội dung chính của bài: {title}")

    article_lines = lines[heading_index:]
    cleaned: list[str] = []
    for line in article_lines:
        stripped = line.strip()
        folded = stripped.casefold()
        if any(folded.startswith(marker.casefold()) for marker in END_MARKERS):
            break
        if re.match(r"^\d+\.\s+bạn đang ở đây", folded):
            break
        if re.match(r"^(?:\*\s+)?\[\]\(javascript:void", stripped):
            continue
        cleaned.append(line.rstrip())

    article_title = title.split("|", 1)[0].strip()
    if cleaned and re.match(r"^#\s+", cleaned[0].lstrip()):
        current_heading = re.sub(r"^#\s+", "", cleaned[0].lstrip()).strip()
        remainder = article_title[len(current_heading):].strip()
        next_content_index = next(
            (index for index in range(1, len(cleaned)) if cleaned[index].strip()),
            None,
        )
        if (
            remainder
            and next_content_index is not None
            and cleaned[next_content_index].strip().casefold() == remainder.casefold()
        ):
            cleaned.pop(next_content_index)
        cleaned[0] = f"# {article_title}"
    elif cleaned and cleaned[0].lstrip().startswith("## "):
        cleaned.insert(0, f"# {article_title}")
        cleaned.insert(1, "")

    compact: list[str] = []
    previous_blank = False
    for line in cleaned:
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue
        compact.append(line)
        previous_blank = is_blank

    content = "\n".join(compact).strip()
    if len(content) < 200:
        raise ValueError(f"Nội dung sau khi làm sạch quá ngắn: {title}")
    return content


async def crawl_article(url: str) -> dict:
    from datetime import datetime
    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        if not result.success:
            raise RuntimeError(f"Crawl failed for {url}: {result.error_message}")

        markdown = result.markdown
        content = markdown.raw_markdown if markdown is not None else ""
        if not content.strip():
            raise ValueError(f"No Markdown content returned for {url}")

        raw_title = (result.metadata or {}).get("title") or "Unknown"
        return {
            "url": url,
            "title": raw_title.split("|", 1)[0].strip(),
            "raw_title": raw_title,
            "date_crawled": datetime.now().astimezone().isoformat(),
            "doc_type": "news",
            "raw_content_markdown": content,
            "content_markdown": clean_article_markdown(content, raw_title),
        }


def clean_saved_articles() -> None:
    """Làm sạch các JSON đã crawl mà không cần tải lại từ website."""
    for path in sorted(DATA_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        raw_content = data.get("raw_content_markdown") or data["content_markdown"]
        raw_title = data.get("raw_title") or data["title"]
        cleaned_content = clean_article_markdown(raw_content, raw_title)
        data["raw_title"] = raw_title
        data["title"] = raw_title.split("|", 1)[0].strip()
        data["doc_type"] = "news"
        data["raw_content_markdown"] = raw_content
        data["content_markdown"] = cleaned_content
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            f"Cleaned: {path.name} "
            f"({len(raw_content)} -> {len(cleaned_content)} chars)"
        )


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
