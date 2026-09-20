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
    "https://uet.vnu.edu.vn/ke-hoach-ket-thuc-khoa-hoc-cua-cac-lop-qh-2021-k66-chuong-trinh-ky-su-cac-khoa-cu-va-tn-truoc-han-dot-xet-thang-01-2026/",
    "https://uet.vnu.edu.vn/thong-bao-so-5-ve-trien-khai-cho-sinh-vien-tham-gia-bhyt-nam-2026/",
    "https://uet.vnu.edu.vn/tham-gia-cuoc-thi-hoc-sinh-sinh-vien-voi-y-tuong-khoi-nghiep/",
    "https://uet.vnu.edu.vn/thong-tin-ve-chuong-trinh-hoc-bong-khoa-hoc-cong-nghe-dao-tao-thac-si-tien-si-du-hoc-nuoc-ngoai-cua-tap-doan-vingroup/",
    "https://uet.vnu.edu.vn/tong-hop-ve-hoc-bong-bac-sau-dai-hoc-tai-uet-nam-2021/",
    "https://uet.vnu.edu.vn/thong-tin-hoc-bong-vingroup/",
]


async def crawl_article(url: str) -> dict:
    """Crawl bài viết bằng Crawl4AI, tự động fallback sang requests/BeautifulSoup nếu cần."""
    from datetime import datetime

    # 1. Thử dùng Crawl4AI trước
    try:
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            if result.success and result.markdown and len(result.markdown.strip()) > 200:
                title = result.metadata.get("title") or "Thông báo UET - VNU"
                return {
                    "url": url,
                    "title": title.strip(),
                    "date_crawled": datetime.now().isoformat(),
                    "content_markdown": result.markdown.strip(),
                }
    except Exception as exc:
        print(f"crawl4ai fallback to soup for {url} (reason: {exc})")

    # 2. Resilient Fallback: Requests + BeautifulSoup
    import requests
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Bóc tách tiêu đề
    title_tag = soup.find("h1", class_="entry-title") or soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Thông báo UET - VNU"

    # Bóc tách phần nội dung chính
    content_area = soup.find("div", class_="entry-content") or soup.find("div", class_="content-detail") or soup.find("article") or soup.body
    
    # Chuyển đổi các thẻ sang Markdown
    lines = [f"# {title}\n"]
    if content_area:
        for element in content_area.find_all(["h1", "h2", "h3", "h4", "p", "li", "table"]):
            if element.name in ["h1", "h2"]:
                lines.append(f"\n## {element.get_text(strip=True)}\n")
            elif element.name in ["h3", "h4"]:
                lines.append(f"\n### {element.get_text(strip=True)}\n")
            elif element.name == "li":
                lines.append(f"- {element.get_text(strip=True)}")
            elif element.name == "p":
                text = element.get_text(strip=True)
                if text:
                    lines.append(f"\n{text}\n")
            elif element.name == "table":
                # Trích xuất bảng đơn giản
                rows = element.find_all("tr")
                for row in rows:
                    cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                    if cols:
                        lines.append("| " + " | ".join(cols) + " |")

    content_markdown = "\n".join(lines).strip()
    if len(content_markdown) < 200:
        content_markdown = f"# {title}\n\n" + (content_area.get_text(separator="\n\n", strip=True) if content_area else "")

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
