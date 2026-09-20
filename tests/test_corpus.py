"""Offline integrity checks for the checked-in admissions corpus."""

import hashlib
import json
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"


def test_legal_manifest_matches_three_readable_unique_pdfs():
    manifest = json.loads((DATA / "legal_sources.json").read_text(encoding="utf-8"))
    pdfs = sorted((DATA / "landing" / "legal").glob("*.pdf"))
    assert len(manifest) == len(pdfs) == 3
    by_name = {item["filename"]: item for item in manifest}
    assert set(by_name) == {path.name for path in pdfs}

    hashes = set()
    for path in pdfs:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes.add(digest)
        assert by_name[path.name]["sha256"] == digest
        assert path.read_bytes().startswith(b"%PDF-")
        reader = PdfReader(path)
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        assert len(reader.pages) >= 10
        assert len(text) >= 10_000
        assert "\ufffd" not in text
    assert len(hashes) == len(pdfs)


def test_five_news_json_files_are_grounded_and_unique():
    paths = sorted((DATA / "landing" / "news").glob("*.json"))
    assert len(paths) == 5
    items = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    assert len({item["url"] for item in items}) == len(items)
    for item in items:
        assert item["url"].startswith("https://xaydungchinhsach.chinhphu.vn/")
        assert item["publisher"] == "Cổng Thông tin điện tử Chính phủ"
        assert item["date_published"]
        assert item["date_crawled"]
        assert len(item["content_markdown"]) >= 500
        assert "\ufffd" not in item["content_markdown"]


def test_standardized_corpus_has_provenance_and_complete_coverage():
    legal = sorted((DATA / "standardized" / "legal").glob("*.md"))
    news = sorted((DATA / "standardized" / "news").glob("*.md"))
    assert len(legal) == 3
    assert len(news) == 5
    for path in legal + news:
        content = path.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        for field in ("title:", "source:", "doc_type:", "url:"):
            assert field in content[:2000]
        assert len(content) >= 200
        assert "\ufffd" not in content
