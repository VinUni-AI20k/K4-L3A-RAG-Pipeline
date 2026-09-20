"""Optional PageIndex Cloud fallback for the textbook and article corpus.

Run ``python -m src.task8_pageindex_vectorless`` once to upload the eight PDFs.
Searching never uploads implicitly, so a missing key or unfinished cloud index
simply leaves the hybrid retrieval path available.
"""

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from .contracts import validate_search_results
from .task4_chunking_indexing import ROOT, load_documents


LANDING_DIR = ROOT / "data" / "landing"
STANDARDIZED_DIR = ROOT / "data" / "standardized"
PDF_CACHE_DIR = ROOT / "pageindex_pdfs"
DOC_IDS_PATH = ROOT / "pageindex_doc_ids.json"
BASE_URL = "https://api.pageindex.ai"
REQUEST_TIMEOUT = (10, 30)
UPLOAD_TIMEOUT = (10, 120)
SEARCH_TIMEOUT_SECONDS = 45
MAX_DOCUMENTS_PER_SEARCH = 3


def _api_key() -> str:
    load_dotenv(ROOT / ".env")
    return os.getenv("PAGEINDEX_API_KEY", "").strip()


def _request(method: str, endpoint: str, api_key: str, **kwargs) -> dict:
    response = requests.request(
        method,
        f"{BASE_URL}{endpoint}",
        headers={"api_key": api_key},
        timeout=kwargs.pop("timeout", REQUEST_TIMEOUT),
        **kwargs,
    )
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise ValueError("PageIndex trả về JSON không hợp lệ")
    return result


def _render_article_pdf(markdown: Path, destination: Path) -> None:
    """Make a searchable, attributed PDF for the cloud API's PDF-only input."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    from xml.sax.saxutils import escape

    font_candidates = [
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    font_path = next((path for path in font_candidates if path.is_file()), None)
    if font_path is None:
        raise RuntimeError("Cần font Unicode Arial hoặc DejaVu Sans để tạo PDF tiếng Việt")
    if "PageIndexUnicode" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("PageIndexUnicode", str(font_path)))

    body = ParagraphStyle(
        "body", fontName="PageIndexUnicode", fontSize=10, leading=15,
        textColor=colors.HexColor("#202b39"), spaceAfter=5,
    )
    heading = ParagraphStyle(
        "heading", parent=body, fontSize=15, leading=21,
        textColor=colors.HexColor("#102b4e"), spaceAfter=12,
    )
    story = []
    for line in markdown.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 5))
        elif stripped == "---":
            story.append(Spacer(1, 10))
        else:
            is_heading = stripped.startswith("# ")
            value = (stripped[2:] if is_heading else stripped).replace("**", "")
            story.append(Paragraph(escape(value), heading if is_heading else body))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".pdf", dir=destination.parent, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        SimpleDocTemplate(
            str(temporary), pagesize=A4, leftMargin=48, rightMargin=48,
            topMargin=45, bottomMargin=45,
        ).build(story)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def _sources() -> dict[str, Path]:
    sources = {}
    for document in load_documents():
        source = document["id"]
        if source.startswith("legal/"):
            pdf = LANDING_DIR / "legal" / f"{Path(source).stem}.pdf"
            if not pdf.is_file():
                raise FileNotFoundError(pdf)
        elif source.startswith("news/"):
            markdown = STANDARDIZED_DIR / source
            pdf = PDF_CACHE_DIR / f"{Path(source).stem}.pdf"
            if not pdf.exists() or pdf.stat().st_mtime_ns < markdown.stat().st_mtime_ns:
                _render_article_pdf(markdown, pdf)
        else:
            raise ValueError(f"Loại nguồn không hỗ trợ: {source}")
        sources[source] = pdf
    return sources


def _read_cache() -> dict:
    if not DOC_IDS_PATH.exists():
        return {}
    result = json.loads(DOC_IDS_PATH.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Cache PageIndex không hợp lệ")
    return result


def _write_cache(cache: dict) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".tmp", dir=ROOT, delete=False
    ) as stream:
        temporary = Path(stream.name)
        json.dump(cache, stream, ensure_ascii=False, indent=2)
    try:
        temporary.replace(DOC_IDS_PATH)
    finally:
        temporary.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def upload_documents() -> None:
    """Explicitly upload eight source PDFs and cache content-addressed doc IDs."""
    api_key = _api_key()
    if not api_key:
        raise RuntimeError("Thiếu PAGEINDEX_API_KEY trong .env; không upload tài liệu")
    cache = _read_cache()
    for source, pdf in _sources().items():
        digest = _sha256(pdf)
        existing = cache.get(source, {})
        if existing.get("sha256") == digest and existing.get("doc_id"):
            print(f"Reused {source}: {existing['doc_id']}", flush=True)
            continue
        with pdf.open("rb") as stream:
            response = _request(
                "POST", "/doc/", api_key,
                files={"file": (pdf.name, stream, "application/pdf")},
                data={"if_retrieval": "true"}, timeout=UPLOAD_TIMEOUT,
            )
        doc_id = response.get("doc_id")
        if not isinstance(doc_id, str) or not doc_id:
            raise ValueError(f"PageIndex không trả doc_id cho {source}")
        cache[source] = {"doc_id": doc_id, "sha256": digest}
        _write_cache(cache)
        print(f"Uploaded {source}: {doc_id}", flush=True)


def _content_parts(node: dict) -> list[tuple[str, int | None]]:
    parts = []
    contents = node.get("relevant_contents", [])
    for item in contents if isinstance(contents, list) else []:
        group = item if isinstance(item, list) else [item]
        for part in group:
            if isinstance(part, dict):
                content = part.get("relevant_content")
                page = part.get("page_index", node.get("page_index"))
                if isinstance(content, str) and content.strip():
                    parts.append((content.strip(), page if isinstance(page, int) else None))
    if not parts and isinstance(node.get("text"), str) and node["text"].strip():
        page = node.get("page_index")
        parts.append((node["text"].strip(), page if isinstance(page, int) else None))
    return parts


def _preferred_sources(query: str, available: dict[str, str]) -> list[str]:
    from .task6_lexical_search import lexical_search

    ranked = []
    for result in lexical_search(query, top_k=30):
        source = result["id"].split("::chunk-", 1)[0]
        if source in available and source not in ranked:
            ranked.append(source)
    return (ranked + [source for source in sorted(available) if source not in ranked])[:MAX_DOCUMENTS_PER_SEARCH]


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Retrieve cloud passages, or return [] when PageIndex is not configured."""
    api_key = _api_key()
    if not api_key or top_k <= 0 or not query.strip():
        return []
    cache = _read_cache()
    document_ids = {
        source: item["doc_id"]
        for source, item in cache.items()
        if isinstance(item, dict) and isinstance(item.get("doc_id"), str)
    }
    if not document_ids:
        return []
    metadata_by_source = {document["id"]: document["metadata"] for document in load_documents()}
    deadline = time.monotonic() + SEARCH_TIMEOUT_SECONDS
    results = []
    seen = set()
    for source in _preferred_sources(query, document_ids):
        if source not in metadata_by_source or time.monotonic() >= deadline:
            break
        doc_id = document_ids[source]
        status = _request("GET", f"/doc/{doc_id}/", api_key, params={"type": "tree"})
        if status.get("status") != "completed" or status.get("retrieval_ready") is False:
            continue
        submission = _request(
            "POST", "/retrieval/", api_key,
            json={"doc_id": doc_id, "query": query, "thinking": False},
        )
        retrieval_id = submission.get("retrieval_id")
        if not retrieval_id:
            continue
        while time.monotonic() < deadline:
            response = _request("GET", f"/retrieval/{retrieval_id}/", api_key)
            if response.get("status") == "failed":
                break
            if response.get("status") == "completed":
                for node_index, node in enumerate(response.get("retrieved_nodes", [])):
                    if not isinstance(node, dict):
                        continue
                    node_id = node.get("node_id", node_index)
                    for part_index, (content, page) in enumerate(_content_parts(node)):
                        result_id = f"pageindex:{doc_id}:{node_id}:{page}:{part_index}"
                        if result_id in seen:
                            continue
                        seen.add(result_id)
                        metadata = {**metadata_by_source[source], "chunk_index": len(results)}
                        if page is not None:
                            metadata["pdf_page"] = page
                        results.append({
                            "id": result_id,
                            "content": content,
                            "score": 1.0 / (len(results) + 1),
                            "metadata": metadata,
                            "retrieval_method": "pageindex",
                        })
                        if len(results) >= top_k:
                            validate_search_results(results, top_k=top_k, expected_method="pageindex")
                            return results
                break
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
    validate_search_results(results, top_k=top_k, expected_method="pageindex")
    return results


if __name__ == "__main__":
    upload_documents()
