"""
Task 2 — Crawl bài viết pháp luật về tái cơ cấu doanh nghiệp nhà nước.

Chủ đề: Xử lý nợ xấu, mua bán nợ, cổ phần hóa doanh nghiệp nhà nước.
Liên quan đến:
    - NĐ 359/2026/NĐ-CP: VAMC (Công ty Quản lý tài sản TCTD)
    - NĐ 358/2026/NĐ-CP: DATC (Công ty Mua bán nợ Việt Nam)
    - NĐ 357/2026/NĐ-CP: Quản lý nguồn thu cổ phần hóa DNNN
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    # NĐ 358 - DATC Công ty mua bán nợ (Báo Nhân Dân)
    "https://nhandan.vn/quy-dinh-moi-ve-co-che-hoat-dong-va-quan-ly-tai-chinh-cua-datc-post850729.html",
    # NĐ 358 - DATC (Báo Đấu Thầu)
    "https://baodauthau.vn/tai-chinh/co-che-quan-ly-tai-chinh-cua-cong-ty-mua-ban-no-datc-tiep-tuc-doi-moi-post188028.html",
    # NĐ 359 - VAMC xử lý nợ xấu (Tạp chí Thị trường Tài chính)
    "https://thitruongtaichinhtiente.vn/vamc-co-the-mua-no-xau-theo-gia-thi-truong-va-bang-trai-phieu-dac-biet-82827.html",
    # NĐ 359 - VAMC (BNews - TTXVN)
    "https://bnews.vn/nghi-dinh-quy-dinh-ve-thanh-lap-to-chuc-hoat-dong-cua-vamc/378234.html",
    # NĐ 357 - Quản lý nguồn thu cổ phần hóa (VOV)
    "https://vov.vn/kinh-te/chinh-phu-ban-hanh-nghi-dinh-ve-quan-ly-su-dung-nguon-thu-co-cau-lai-von-nha-nuoc-post1185000.vov",
]


def html_to_markdown(html_content: str) -> str:
    """Chuyển đổi HTML thô thành markdown đơn giản."""
    html_content = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1\n", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1\n", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1\n", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<br\s*/?>", "\n", html_content)
    html_content = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<[^>]+>", "", html_content)
    html_content = html_content.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    html_content = html_content.replace("&nbsp;", " ").replace("&quot;", '"').replace("&#39;", "'")
    html_content = re.sub(r"\n{3,}", "\n\n", html_content)
    html_content = re.sub(r" {2,}", " ", html_content)
    return html_content.strip()


async def crawl_with_crawl4ai(url: str) -> dict:
    """Crawl bằng Crawl4AI (ưu tiên dùng nếu có)."""
    from crawl4ai import AsyncWebCrawler
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        title = result.metadata.get("title", "") if result.metadata else ""
        return {
            "url": url,
            "title": title or "Unknown",
            "date_crawled": datetime.now().isoformat(),
            "content_markdown": result.markdown or "",
        }


def crawl_with_requests(url: str) -> dict:
    """Fallback: crawl bằng requests + parse HTML thủ công."""
    import urllib.request
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")

    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.DOTALL | re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else "Unknown"
    title = re.sub(r"<[^>]+>", "", title).strip()

    content_raw = raw
    for pattern in [
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*class="[^"]*(?:article|content|post|detail|body|main)[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*id="[^"]*(?:content|article|main|post)[^"]*"[^>]*>(.*?)</div>',
    ]:
        match = re.search(pattern, raw, re.DOTALL | re.IGNORECASE)
        if match and len(match.group(1)) > 500:
            content_raw = match.group(1)
            break

    content_markdown = html_to_markdown(content_raw)
    if len(content_markdown) < 200:
        content_markdown = html_to_markdown(raw)

    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now().isoformat(),
        "content_markdown": content_markdown,
    }


async def crawl_article(url: str) -> dict:
    """Crawl một URL: ưu tiên Crawl4AI, fallback sang requests."""
    try:
        return await crawl_with_crawl4ai(url)
    except Exception as e1:
        print(f"  [Crawl4AI: {type(e1).__name__}] → dùng requests fallback...")
        return crawl_with_requests(url)


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Crawling {len(ARTICLE_URLS)} URLs → {DATA_DIR}\n")

    success = 0
    for index, url in enumerate(ARTICLE_URLS, 1):
        print(f"[{index}/{len(ARTICLE_URLS)}] {url}")
        try:
            article = await crawl_article(url)
            if len(article.get("content_markdown", "")) < 200:
                print(f"  ⚠️  Nội dung quá ngắn ({len(article.get('content_markdown', ''))} ký tự)")
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            char_count = len(article["content_markdown"])
            print(f"  ✅ {output.name} | '{article['title'][:55]}' | {char_count} ký tự")
            success += 1
        except Exception as error:
            print(f"  ❌ Failed: {error}")

    print(f"\n{'='*55}")
    print(f"Hoàn thành: {success}/{len(ARTICLE_URLS)} bài crawl thành công.")
    print(f"Thư mục: {DATA_DIR}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
