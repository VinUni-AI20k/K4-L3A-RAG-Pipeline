"""
Task 2 — Crawl Etomidate / Pod Chill public articles.

Raw article data is stored in:
    data/landing/news/

Each JSON preserves provenance metadata for later citation.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "landing" / "news"


ARTICLES = [
    {
        "source_id": "bocongan_20260706_etomidate_quang_ninh",
        "publisher": "Bộ Công an",
        "published_date": "2026-07-06",
        "url": (
            "https://bocongan.gov.vn/bai-viet/"
            "cong-an-tinh-quang-ninh-quyet-liet-dau-tranh-xu-ly-"
            "toi-pham-lien-quan-den-chat-ma-tuy-moi-etomidate-1783415450"
        ),
    },
    {
        "source_id": "bocongan_20260717_pod_chill_quang_ninh",
        "publisher": "Bộ Công an",
        "published_date": "2026-07-17",
        "url": (
            "https://bocongan.gov.vn/bai-viet/"
            "cong-an-tinh-quang-ninh-triet-pha-duong-day-mua-ban-"
            "to-chuc-su-dung-ma-tuy-etomidate-duoi-dang-pod-chill-"
            "tai-mong-cai-1784272382"
        ),
    },
    {
        "source_id": "vtv_20260725_pod_chill_etomidate",
        "publisher": "VTV",
        "published_date": "2026-07-25",
        "url": (
            "https://vtv.vn/"
            "pod-chill-chua-etomidate-hiem-hoa-ma-tuy-moi-doi-lot-"
            "thuoc-la-dien-tu-100260725185715661.htm"
        ),
    },
    {
        "source_id": "bocongan_20260802_etomidate_hcm",
        "publisher": "Bộ Công an",
        "published_date": "2026-08-02",
        "url": (
            "https://bocongan.gov.vn/bai-viet/"
            "cong-an-thanh-pho-ho-chi-minh-tiep-tuc-triet-pha-"
            "duong-day-ma-tuy-etomidate-doi-lot-pod-chill-bat-giu-"
            "va-xu-ly-37-doi-tuong-1785643233"
        ),
    },
    {
        "source_id": "bocongan_20260828_etomidate_hanoi",
        "publisher": "Bộ Công an",
        "published_date": "2026-08-28",
        "url": (
            "https://www.bocongan.gov.vn/bai-viet/"
            "cong-an-ha-noi-triet-pha-duong-day-mua-ban-san-chiet-"
            "tinh-dau-ma-tuy-cuc-lon-nup-bong-thuoc-la-dien-tu-"
            "giao-dich-khoang-100-ty-dong-1787893865"
        ),
    },
]


def sha256_text(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


async def crawl_article(article_spec: dict) -> dict:
    from crawl4ai import AsyncWebCrawler

    url = article_spec["url"]

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)

    if not result.success:
        raise RuntimeError(
            result.error_message or "Unknown crawl error"
        )

    # crawl4ai versions may expose markdown differently.
    markdown = result.markdown

    if hasattr(markdown, "raw_markdown"):
        markdown = markdown.raw_markdown

    markdown = str(markdown or "").strip()

    if len(markdown) < 300:
        raise ValueError(
            f"Content too short ({len(markdown)} chars)"
        )

    metadata = result.metadata or {}

    title = (
        metadata.get("title")
        or metadata.get("og:title")
        or article_spec["source_id"]
    )

    return {
        "source_id": article_spec["source_id"],
        "title": title.strip(),
        "publisher": article_spec["publisher"],
        "published_date": article_spec["published_date"],

        "url": url,
        "canonical_url": url,

        "source_type": "official_news"
        if article_spec["publisher"] == "Bộ Công an"
        else "trusted_news",

        "trust_level": "official"
        if article_spec["publisher"] == "Bộ Công an"
        else "trusted",

        "date_crawled": datetime.now(
            timezone.utc
        ).isoformat(),

        "content_markdown": markdown,
        "content_sha256": sha256_text(markdown),
    }


async def crawl_all() -> None:
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    success = 0
    failed = 0

    for index, article_spec in enumerate(ARTICLES, 1):
        source_id = article_spec["source_id"]
        output = DATA_DIR / f"{source_id}.json"

        print("\n" + "=" * 70)
        print(f"[{index}/{len(ARTICLES)}] {source_id}")

        # Idempotent
        if output.exists() and output.stat().st_size > 500:
            print(f"SKIP existing: {output.name}")
            success += 1
            continue

        try:
            article = await crawl_article(article_spec)

            output.write_text(
                json.dumps(
                    article,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            print(
                f"SAVED: {output.name} "
                f"({len(article['content_markdown'])} chars)"
            )

            success += 1

        except Exception as error:
            failed += 1
            print(
                f"FAILED: {article_spec['url']}\n"
                f"Reason: {error}"
            )

    print("\n" + "=" * 70)
    print(f"SUCCESS: {success}")
    print(f"FAILED : {failed}")


if __name__ == "__main__":
    asyncio.run(crawl_all())