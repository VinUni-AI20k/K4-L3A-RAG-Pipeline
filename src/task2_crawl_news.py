import asyncio
import csv
import json
from datetime import datetime
from pathlib import Path

async def crawl_article(url: str) -> dict:
    """Crawl bài viết bằng Crawl4AI, có fallback sang httpx + bs4 nếu browser lỗi."""
    date_crawled = datetime.now().isoformat()

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


async def crawl_all(news_list: list, output_dir: Path) -> None:
    """Crawl và lưu từng bài thành một file JSON theo short_name."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for index, item in enumerate(news_list, 1):
        short_name = item['short_name'].strip()
        url = item['url'].strip()
        
        try:
            print(f"[{index}/{len(news_list)}] Crawling: {short_name} ({url})...")
            article = await crawl_article(url)
            
            output = output_dir / f"{short_name}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f" -> Saved: {output.name} (Title: {article.get('title')[:40]}...)")
        except Exception as error:
            print(f" -> Failed: {url} — {error}")


def main():
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    INPUT_CSV = BASE_DIR / "news_urls.csv"
    OUTPUT_DIR = BASE_DIR / "data" / "landing" / "news"

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Không tìm thấy file danh sách link tại: {INPUT_CSV}")

    news_to_crawl = []
    with open(INPUT_CSV, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('short_name') and row.get('url'):
                news_to_crawl.append(row)

    print(f"[*] Tổng cộng có {len(news_to_crawl)} bài viết cần thu thập.")
    
    # Khởi chạy bất đồng bộ
    asyncio.run(crawl_all(news_to_crawl, OUTPUT_DIR))


if __name__ == "__main__":
    main()