"""Task 2 — Thu thập bài viết về du lịch và ẩm thực Việt Nam.

Crawl4AI được ưu tiên khi đã cài đặt. Nếu môi trường chưa có Crawl4AI hoặc
một trang không render được bằng trình duyệt, script tự chuyển sang HTTP để
vẫn có thể thu thập các trang public có HTML dựng sẵn từ server.
"""

import asyncio
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlparse

import requests


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"
MIN_CONTENT_LENGTH: Final = 200
REQUEST_TIMEOUT: Final = (10, 60)

ARTICLE_URLS = [
    "https://xeduykhang.vn/toplist-cac-dia-diem-du-lich-am-thuc-ha-noi/",
    "https://vinpearl.com/vi/food-tour-ha-noi/",
    "https://vietnamtourism.gov.vn/post/57557",
    "https://www.traveloka.com/vi-vn/explore/tips/ta-du-lich-am-thuc/594913",
    "https://vietnamtourism.gov.vn/post/50203",
    "https://www.traveloka.com/vi-vn/explore/culinary/am-thuc-cao-bang/258281",
    "https://vietnamtourism.gov.vn/post/48997",
    "https://vietnamtourism.gov.vn/post/53182",
    "https://vietnamtourism.gov.vn/post/52872",
    "https://www.traveloka.com/vi-vn/explore/culinary/dac-san-thanh-hoa/164310",
]


class _ArticleHTMLParser(HTMLParser):
    """Trích xuất title và phần nội dung đọc được từ HTML mà không cần JS."""

    ignored_tags = {
        "script", "style", "noscript", "nav", "footer", "aside", "form", "svg"
    }
    block_tags = {"p", "div", "section", "article", "main", "blockquote", "br"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.meta_title = ""
        self.all_parts: list[str] = []
        self.focused_parts: list[str] = []
        self._ignored_depth = 0
        self._focused_depth = 0
        self._in_title = False

    def _append(self, value: str) -> None:
        self.all_parts.append(value)
        if self._focused_depth:
            self.focused_parts.append(value)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = {key.lower(): value or "" for key, value in attrs}

        if tag in self.ignored_tags:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return

        if tag in {"article", "main"}:
            self._focused_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta" and attributes.get("property", "").lower() == "og:title":
            self.meta_title = attributes.get("content", "").strip()

        if tag in self.block_tags:
            self._append("\n\n")
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._append(f"\n\n{'#' * int(tag[1])} ")
        elif tag == "li":
            self._append("\n- ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.ignored_tags:
            if self._ignored_depth:
                self._ignored_depth -= 1
            return
        if self._ignored_depth:
            return

        if tag == "title":
            self._in_title = False
        if tag in self.block_tags or tag in {
            "h1", "h2", "h3", "h4", "h5", "h6", "li"
        }:
            self._append("\n")
        if tag in {"article", "main"} and self._focused_depth:
            self._focused_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        value = re.sub(r"\s+", " ", data).strip()
        if not value:
            return
        if self._in_title:
            self.title_parts.append(value)
        self._append(value + " ")

    @property
    def title(self) -> str:
        return self.meta_title or " ".join(self.title_parts).strip()

    @property
    def markdown(self) -> str:
        focused = "".join(self.focused_parts)
        content = (
            focused
            if len(focused.strip()) >= MIN_CONTENT_LENGTH
            else "".join(self.all_parts)
        )
        content = re.sub(r"[ \t]+\n", "\n", content)
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content.strip()


def _validate_article(article: object) -> None:
    if not isinstance(article, dict):
        raise ValueError("Dữ liệu bài viết phải là dictionary")
    for field in ("url", "title", "date_crawled", "content_markdown"):
        if not isinstance(article.get(field), str) or not article[field].strip():
            raise ValueError(f"Bài viết thiếu trường hợp lệ: {field}")
    if article["title"].strip().lower() in {"none", "null", "unknown"}:
        raise ValueError("Tiêu đề bài viết không hợp lệ")
    if len(article["content_markdown"].strip()) < MIN_CONTENT_LENGTH:
        raise ValueError("Nội dung bài viết quá ngắn")


def _markdown_from_crawl4ai(result: Any) -> str:
    markdown = getattr(result, "markdown", "")
    if isinstance(markdown, str):
        return markdown.strip()
    for attribute in ("fit_markdown", "raw_markdown"):
        value = getattr(markdown, attribute, "")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


async def _crawl_with_http(url: str) -> tuple[str, str]:
    def fetch(target_url: str) -> requests.Response:
        response = requests.get(
            target_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "Chrome/124.0 Safari/537.36"
                )
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response

    parsed_url = urlparse(url)
    if parsed_url.hostname == "vietnamtourism.gov.vn" and parsed_url.path.startswith("/post/"):
        post_id = parsed_url.path.rstrip("/").rsplit("/", 1)[-1]
        api_url = f"https://public.vietnamtourism.gov.vn/post/{post_id}"
        response = await asyncio.to_thread(fetch, api_url)
        payload = response.json()
        parser = _ArticleHTMLParser()
        parser.feed(f"{payload.get('summary', '')}\n{payload.get('content', '')}")
        return str(payload.get("title") or "").strip(), parser.markdown

    response = await asyncio.to_thread(fetch, url)
    parser = _ArticleHTMLParser()
    parser.feed(response.text)
    return parser.title, parser.markdown


async def crawl_article(url: str, crawler: Any | None = None) -> dict[str, str]:
    """Crawl một URL và trả dữ liệu theo schema dùng chung của Task 2."""
    title = ""
    content = ""

    if crawler is not None:
        try:
            result = await asyncio.wait_for(crawler.arun(url=url), timeout=45)
            if getattr(result, "success", True) is False:
                message = getattr(result, "error_message", "Crawl4AI thất bại")
                raise RuntimeError(message)
            metadata = getattr(result, "metadata", {}) or {}
            title_value = metadata.get("title")
            title = str(title_value).strip() if title_value else ""
            content = _markdown_from_crawl4ai(result)
        except Exception as error:
            print(f"Crawl4AI không đọc được {url}; chuyển sang HTTP ({error})")

    if not title or len(content) < MIN_CONTENT_LENGTH:
        http_title, http_content = await _crawl_with_http(url)
        title = title or http_title
        if len(http_content) > len(content):
            content = http_content

    article = {
        "url": url,
        "title": title,
        "date_crawled": datetime.now(timezone.utc).isoformat(),
        "content_markdown": content,
    }
    _validate_article(article)
    return article


def _load_cached_article(path: Path, url: str) -> dict[str, str] | None:
    try:
        article = json.loads(path.read_text(encoding="utf-8"))
        _validate_article(article)
        if article["url"] != url:
            return None
        return article
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return None


def _save_article(path: Path, article: dict[str, str]) -> None:
    temporary_path = path.with_suffix(".json.part")
    try:
        temporary_path.write_text(
            json.dumps(article, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


async def _crawl_and_save(crawler: Any | None) -> tuple[int, int]:
    saved = 0
    failed = 0
    for index, url in enumerate(ARTICLE_URLS, 1):
        output = DATA_DIR / f"article_{index:02d}.json"
        if _load_cached_article(output, url) is not None:
            print(f"Đã có: {output.name}")
            saved += 1
            continue
        try:
            article = await crawl_article(url, crawler)
            _save_article(output, article)
            print(f"Đã lưu: {output.name} — {article['title']}")
            saved += 1
        except Exception as error:
            print(f"Thất bại: {url} — {error}")
            failed += 1
    return saved, failed


async def crawl_all() -> None:
    """Crawl các URL và lưu mỗi bài thành một JSON riêng biệt."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cached_count = sum(
        _load_cached_article(DATA_DIR / f"article_{index:02d}.json", url) is not None
        for index, url in enumerate(ARTICLE_URLS, 1)
    )
    if cached_count == len(ARTICLE_URLS):
        print(f"Hoàn tất: {cached_count}/{len(ARTICLE_URLS)} bài hợp lệ trong cache.")
        return

    # Crawl4AI mặc định ghi cache vào home; dùng /tmp để chạy được cả trong
    # container hoặc môi trường có home chỉ-đọc.
    os.environ.setdefault(
        "CRAWL4_AI_BASE_DIRECTORY",
        str(Path(tempfile.gettempdir()) / "k4_day08_crawl4ai"),
    )

    try:
        from crawl4ai import AsyncWebCrawler
    except (ImportError, OSError) as error:
        print(f"Không dùng được Crawl4AI; sử dụng HTTP fallback ({error})")
        saved, failed = await _crawl_and_save(None)
    else:
        crawler = AsyncWebCrawler()
        try:
            await asyncio.wait_for(crawler.start(), timeout=30)
            saved, failed = await _crawl_and_save(crawler)
        except Exception as error:
            print(f"Không khởi động được Crawl4AI; sử dụng HTTP fallback ({error})")
            saved, failed = await _crawl_and_save(None)
        finally:
            try:
                await crawler.close()
            except Exception:
                pass

    print(f"Hoàn tất: {saved}/{len(ARTICLE_URLS)} bài hợp lệ, {failed} thất bại.")
    if saved < 5:
        raise RuntimeError("Task 2 cần ít nhất 5 bài viết hợp lệ")


if __name__ == "__main__":
    asyncio.run(crawl_all())
