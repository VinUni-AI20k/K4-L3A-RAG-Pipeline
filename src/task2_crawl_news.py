"""
Task 2 — Crawl bài viết/thông báo.

Chủ đề: Quy chế đào tạo, tuyển sinh và pháp luật giáo dục đại học, sau đại học.
"""

import asyncio
from datetime import datetime
import json
from pathlib import Path
import re
import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://baochinhphu.vn/de-xuat-moi-quy-che-dao-tao-trinh-do-dai-hoc-102260604154823405.htm",
    "https://baochinhphu.vn/quy-che-tuyen-sinh-va-dao-tao-sau-dai-hoc-102260715150935315.htm",
    "https://luatvietnam.vn/tin-van-ban-moi/quyet-dinh-39-2026-qd-ttg-chuong-trinh-dao-tao-dai-hoc-toi-thieu-120-tin-chi-thac-si-tu-45-tin-chi-186-110858-article.html",
    "https://luatvietnam.vn/linh-vuc-khac/quy-dinh-ve-hoc-lien-thong-thay-doi-the-nao-tu-15-8-2026-883-110951-article.html",
    "https://baochinhphu.vn/lien-ket-dao-tao-dai-hoc-thac-si-tien-si-giua-viet-nam-va-nuoc-ngoai-102250415165737313.htm",
]


def extract_clean_article(url: str) -> dict:
    """Tải và bóc tách nội dung bài viết tin tức chính thống."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.encoding = "utf-8"
    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    # 1. Trích xuất tiêu đề
    title_elem = soup.find("h1") or soup.find("title")
    title = title_elem.get_text().strip() if title_elem else "Bài viết chính sách giáo dục đại học"
    title = re.sub(r"\s+", " ", title)

    # 2. Trích xuất nội dung chính
    content_div = (
        soup.find("div", class_="detail-content")
        or soup.find("div", class_="content-detail")
        or soup.find("div", id="main-content")
        or soup.find("div", class_="the-article-body")
        or soup.find("article")
    )
    
    if content_div:
        # Loại bỏ script, style, quảng cáo
        for tag in content_div(["script", "style", "nav", "aside", "figure"]):
            tag.decompose()
        paragraphs = [p.get_text().strip() for p in content_div.find_all(["p", "h2", "h3"]) if p.get_text().strip()]
        body_text = "\n\n".join(paragraphs)
    else:
        # Fallback text stripping
        body_text = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        body_text = re.sub(r"<style.*?</style>", "", body_text, flags=re.DOTALL | re.IGNORECASE)
        body_text = re.sub(r"<[^>]+>", " ", body_text)
        body_text = re.sub(r"\s+", " ", body_text).strip()

    markdown = f"# {title}\n\n" + body_text

    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now().strftime("%Y-%m-%d"),
        "content_markdown": markdown,
    }


async def crawl_article(url: str) -> dict:
    """Async wrapper cho việc crawl."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, extract_clean_article, url)



async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for index, url in enumerate(ARTICLE_URLS, 1):
        output = DATA_DIR / f"article_{index:02d}.json"
        if output.exists():
            print(f"Already exists: {output.name}")
            continue

        try:
            article = await crawl_article(url)
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved: {output}")
        except Exception as error:
            print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
