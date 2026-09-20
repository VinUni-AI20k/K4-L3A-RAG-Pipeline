"""Task 8: PageIndex Cloud vectorless retrieval, configured through .env.

Uses endpoints supported by pageindex 0.2.8, with explicit HTTP timeouts.
PageIndex selects pages; only original OCR text is returned as evidence.
No local search and no upload during chat. Prepare with python -m src.task8_pageindex_vectorless.
"""
import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
STANDARDIZED_DIR = ROOT_DIR / "data" / "standardized"
CACHE_PATH = ROOT_DIR / "pageindex_doc_ids.json"
PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
logger = logging.getLogger(__name__)


def _load_cache() -> dict:
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _request(method: str, path: str, timeout: float, **kwargs) -> dict:
    key = os.getenv("PAGEINDEX_API_KEY", PAGEINDEX_API_KEY)
    if not key:
        raise ValueError("PAGEINDEX_API_KEY is not configured")
    if timeout <= 0:
        raise TimeoutError("PageIndex time budget exhausted")
    response = requests.request(
        method, f"https://api.pageindex.ai/{path.lstrip('/')}",
        headers={"api_key": key}, timeout=timeout, **kwargs,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Invalid PageIndex response")
    return payload


def _documents() -> list[dict]:
    from .task4_chunking_indexing import load_documents
    return load_documents()


def _fingerprint(doc: dict) -> str:
    return hashlib.sha256(doc["content"].encode("utf-8")).hexdigest()


def upload_documents() -> None:
    """Upload Unicode PDFs rendered from canonical Markdown; reuse unchanged IDs.

    Page references point to generated PDFs, not the publisher's original pages.
    Each success is saved immediately so a failed batch can safely resume.
    """
    if not os.getenv("PAGEINDEX_API_KEY", PAGEINDEX_API_KEY):
        raise ValueError("Set PAGEINDEX_API_KEY in .env before uploading")
    from fpdf import FPDF
    fonts = [os.getenv("PAGEINDEX_FONT", ""), "C:/Windows/Fonts/arial.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    font = next((Path(p) for p in fonts if p and Path(p).is_file()), None)
    if font is None:
        raise ValueError("Set PAGEINDEX_FONT to a Unicode TrueType font")
    cache = _load_cache()
    pdf_dir = ROOT_DIR / "pageindex_pdfs"
    pdf_dir.mkdir(exist_ok=True)
    for doc in _documents():
        digest = _fingerprint(doc)
        cached = cache.get(doc["id"], {})
        if cached.get("sha256") == digest and cached.get("doc_id"):
            continue
        pdf = FPDF()
        pdf.add_font("Unicode", fname=str(font))
        pdf.set_font("Unicode", size=11)
        pdf.add_page()
        pdf.multi_cell(0, 6, doc["content"])
        path = pdf_dir / f"{digest}.pdf"
        pdf.output(str(path))
        with path.open("rb") as stream:
            response = _request("POST", "doc/", float(os.getenv("PAGEINDEX_UPLOAD_TIMEOUT", "60")),
                                files={"file": (path.name, stream, "application/pdf")},
                                data={"if_retrieval": True})
        doc_id = response.get("doc_id")
        if not isinstance(doc_id, str) or not doc_id:
            raise ValueError("PageIndex did not return doc_id")
        cache[doc["id"]] = {"sha256": digest, "doc_id": doc_id, "filename": path.name}
        temporary = CACHE_PATH.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(CACHE_PATH)


def _search(query: str, top_k: int) -> list[dict]:
    cache = _load_cache()
    documents = {}
    aliases = {}
    for doc in _documents():
        entry = cache.get(doc["id"], {})
        if entry.get("sha256") == _fingerprint(doc) and entry.get("doc_id"):
            doc_id = entry["doc_id"]
            documents[doc_id] = doc
            aliases[doc_id] = doc_id
            aliases[entry.get("filename", "")] = doc_id
    if not documents:
        logger.warning("No current PageIndex IDs; run the Task 8 upload command first")
        return []
    deadline = time.monotonic() + float(os.getenv("PAGEINDEX_TIMEOUT", "45"))
    response = _request("POST", "chat/completions/", deadline - time.monotonic(), json={
        "doc_id": list(documents), "stream": False, "enable_citations": True,
        "temperature": 0,
        "messages": [{"role": "user", "content": query}],
    })
    # The installed SDK has chat_completions, not client.search(). Citation tags
    # are documented as <doc=filename.pdf;page=1;block=...> (block is optional).
    answer = response["choices"][0]["message"]["content"]
    selected = []
    for name, page in re.findall(r"<doc=([^;>]+);page=(\d+)(?:;[^>]*)?>", answer):
        doc_id = aliases.get(name)
        pair = (doc_id, int(page))
        if doc_id and int(page) > 0 and pair not in selected:
            selected.append(pair)
    pages_by_doc, results = {}, []
    for doc_id, number in selected:
        if len(results) >= top_k or time.monotonic() >= deadline:
            break
        if doc_id not in pages_by_doc:
            payload = _request("GET", f"doc/{doc_id}/", deadline - time.monotonic(),
                               params={"type": "ocr", "format": "page"})
            pages_by_doc[doc_id] = {
                p["page_index"]: p["markdown"] for p in payload.get("result", [])
                if isinstance(p, dict) and isinstance(p.get("page_index"), int)
                and isinstance(p.get("markdown"), str)
            } if payload.get("status") == "completed" else {}
        content = pages_by_doc[doc_id].get(number, "")
        if not content.strip():
            continue
        doc = documents[doc_id]
        results.append({
            "id": f"{doc['id']}::page-{number}", "content": content,
            "score": 1.0 / (len(results) + 1),
            "retrieval_method": "pageindex",
            "metadata": {**doc["metadata"], "document_id": doc["id"],
                         "pageindex_doc_id": doc_id, "chunk_index": number - 1,
                         "page_number": number, "page_kind": "generated_pdf",
                         "score_kind": "reciprocal_citation_rank"},
        })
    return results


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Return cloud page evidence; missing key, timeout or provider failure => [].

    PageIndex does not expose calibrated confidence; score is reciprocal citation
    order, explicitly labelled in metadata. The caller may retain hybrid results.
    """
    if not query.strip() or top_k <= 0 or not os.getenv("PAGEINDEX_API_KEY", PAGEINDEX_API_KEY):
        return []
    try:
        return _search(query, top_k)
    except (requests.RequestException, TimeoutError, ValueError, KeyError, TypeError, IndexError) as exc:
        logger.warning("PageIndex unavailable (%s)", type(exc).__name__)
        return []


if __name__ == "__main__":
    upload_documents()
