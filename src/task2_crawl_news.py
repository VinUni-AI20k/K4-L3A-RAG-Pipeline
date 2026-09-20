"""Crawl official Government news and guidance for 2026 admissions."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://xaydungchinhsach.chinhphu.vn/toan-van-cong-van-2304-bgddt-gddh-huong-dan-tuyen-sinh-dai-hoc-cao-dang-2026-119260505052505936.htm",
    "https://xaydungchinhsach.chinhphu.vn/tuyen-sinh-2026-cac-moc-thoi-gian-quan-trong-thi-sinh-can-nho-119260206155449664.htm",
    "https://xaydungchinhsach.chinhphu.vn/chinh-sach-uu-tien-trong-tuyen-sinh-dai-hoc-119260227153842885.htm",
    "https://xaydungchinhsach.chinhphu.vn/huong-dan-thanh-toan-truc-tuyen-le-phi-xet-tuyen-dai-hoc-2026-119260716115111114.htm",
    "https://xaydungchinhsach.chinhphu.vn/nhung-diem-moi-trong-quy-che-tuyen-sinh-dai-hoc-2026-119260215183555963.htm",
]


def _clean_text(value: str) -> str:
    return re.sub(r"[ \t]+", " ", value.replace("\xa0", " ")).strip()


def _table_to_markdown(table: Tag) -> str:
    rows = []
    for row in table.find_all("tr"):
        cells = [
            _clean_text(cell.get_text(" ", strip=True))
            for cell in row.find_all(["th", "td"])
        ]
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    header = rows[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines)


def _html_to_markdown(container: Tag) -> str:
    """Preserve useful structure while dropping navigation, ads and scripts."""
    for unwanted in container.select("script, style, noscript, iframe"):
        unwanted.decompose()

    blocks: list[str] = []
    for element in container.find_all(["h1", "h2", "h3", "h4", "p", "li", "table"]):
        if element.find_parent("table") and element.name != "table":
            continue
        if element.name == "table":
            block = _table_to_markdown(element)
        else:
            content = _clean_text(element.get_text(" ", strip=True))
            if not content:
                continue
            if element.name and element.name.startswith("h"):
                block = f"{'#' * int(element.name[1])} {content}"
            elif element.name == "li":
                block = f"- {content}"
            else:
                block = content
        if block and (not blocks or block != blocks[-1]):
            blocks.append(block)
    return "\n\n".join(blocks).strip()


def _fetch_article(url: str) -> dict:
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    response = session.get(
        url,
        timeout=60,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/140.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "vi,en;q=0.8",
        },
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    title = _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    content = soup.select_one(".detail-content")
    if not title or content is None:
        raise ValueError(f"Could not locate title/article body at {url}")
    markdown = _html_to_markdown(content)
    if len(markdown) < 500:
        raise ValueError(f"Article body is unexpectedly short at {url}")

    published = None
    detail_main = soup.select_one(".detail-main")
    if detail_main:
        match = re.search(
            r"\b(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}\b",
            detail_main.get_text(" ", strip=True),
        )
        if match:
            published = datetime.strptime(match.group(1), "%d/%m/%Y").date().isoformat()

    return {
        "url": url,
        "title": title,
        "date_published": published,
        "date_crawled": datetime.now(timezone.utc).isoformat(),
        "publisher": "Cổng Thông tin điện tử Chính phủ",
        "topic": "Tuyển sinh đại học Việt Nam năm 2026",
        "content_markdown": markdown,
    }


async def crawl_article(url: str) -> dict:
    """Download and parse one public article without blocking the event loop."""
    return await asyncio.to_thread(_fetch_article, url)


def _slug_from_url(url: str) -> str:
    slug = Path(urlparse(url).path).stem
    slug = re.sub(r"-119\d+$", "", slug)
    return re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_")[:90]


async def crawl_all() -> None:
    """Crawl all configured articles and fail if any required source fails."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # The Government portal occasionally closes bursts of concurrent requests.
    # Fetch sequentially so this reproducible collector remains polite/reliable.
    results = []
    for url in ARTICLE_URLS:
        results.append(await crawl_article(url))
    for index, article in enumerate(results, 1):
        output = DATA_DIR / f"{index:02d}_{_slug_from_url(article['url'])}.json"
        output.write_text(
            json.dumps(article, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Saved: {output}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
