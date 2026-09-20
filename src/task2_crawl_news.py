"""Task 2 - Crawl at least 5 public news articles into landing JSON files.

The JSON files must contain:
    url, title, date_crawled, content_markdown

This implementation uses Playwright's browser context to fetch text after
client-side rendering, then converts the main article HTML to lightweight
Markdown using Markdownify. If a page is blocked by WAF/captcha, the URL is
skipped and reported rather than bypassed.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://vietnamtourism.gov.vn/post/56914",
    "https://baochinhphu.vn/kiem-tra-ra-soat-dieu-kien-an-toan-ky-thuat-cua-toan-bo-doi-tau-du-lich-tren-vinh-ha-long-102260302093206248.htm",
    "https://www.vietnam.travel/vi/node/1505",
    "https://vietnamnet.vn/vinh-ha-long-nam-trong-top-10-diem-den-dep-nhat-the-gioi-nam-2022-2052244.html",
    "https://vietnamtourism.gov.vn/post/48907",
]


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/125 Safari/537.36"
)


def html_to_markdown(html: str) -> str:
    """Extract the most likely article region and convert to Markdown."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "header", "footer", "nav"]):
        tag.decompose()

    article = (
        soup.find("article")
        or soup.find("main")
        or soup.find("div", class_="content")
        or soup.body
    )
    if article is None:
        raise RuntimeError("could not find page article content")

    return md(str(article), heading_style="ATX").strip()


async def crawl_article(browser, url: str) -> dict:
    """Fetch one page and return a landing JSON document."""
    context = await browser.new_context(user_agent=USER_AGENT, locale="vi-VN")
    page = await context.new_page()
    try:
        try:
            response = await page.goto(url, wait_until="networkidle", timeout=25_000)
        except Exception:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=25_000)
        status = response.status if response is not None else None
        if status not in (None, 200):
            raise RuntimeError(f"unexpected HTTP status {status}")
        try:
            await page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass

        title = (await page.title()).strip()
        html = await page.content()

        if not title:
            h1 = await page.query_selector("h1")
            if h1:
                title = (await h1.inner_text()).strip()

        markdown = html_to_markdown(html)
        if len(markdown.strip()) < 200:
            raise RuntimeError("article markdown is too short")

        return {
            "url": page.url or url,
            "title": " ".join(title.split()),
            "date_crawled": datetime.now().isoformat(),
            "content_markdown": markdown,
        }
    finally:
        await context.close()


async def crawl_all() -> None:
    """Crawl and save each article as one JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        for index, url in enumerate(ARTICLE_URLS, 1):
            output = DATA_DIR / f"article_{index:02d}.json"
            try:
                article = await crawl_article(browser, url)
                output.write_text(
                    json.dumps(article, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"Saved: {output.name} ({len(article['content_markdown'])} chars)")
            except Exception as error:
                print(f"Failed: {url} - {type(error).__name__}: {error}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(crawl_all())
