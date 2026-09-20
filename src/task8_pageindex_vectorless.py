"""Task 8: PageIndex vectorless retrieval with a failure-safe fallback.

PageIndex 0.2.8 exposes asynchronous document and retrieval REST endpoints.
This module calls those endpoints directly because that SDK release does not
forward request timeouts. No network call is made when ``PAGEINDEX_API_KEY`` is
not configured.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from .contracts import validate_search_results
from .task4_chunking_indexing import load_documents


PROJECT_DIR = Path(__file__).resolve().parent.parent
STANDARDIZED_DIR = PROJECT_DIR / "data" / "standardized"
LANDING_LEGAL_DIR = PROJECT_DIR / "data" / "landing" / "legal"
PDF_CACHE_DIR = PROJECT_DIR / "pageindex_pdfs"
CACHE_PATH = PROJECT_DIR / "pageindex_doc_ids.json"

PAGEINDEX_BASE_URL = "https://api.pageindex.ai"
PAGEINDEX_API_KEY = ""
REQUEST_TIMEOUT = 30.0
RETRIEVAL_TIMEOUT = 120.0
POLL_INTERVAL = 2.0
MAX_WORKERS = 4


def _settings() -> tuple[str, str, float, float, float]:
    load_dotenv(PROJECT_DIR / ".env")
    api_key = os.getenv("PAGEINDEX_API_KEY", PAGEINDEX_API_KEY).strip()
    base_url = os.getenv("PAGEINDEX_BASE_URL", PAGEINDEX_BASE_URL).rstrip("/")
    request_timeout = float(os.getenv("PAGEINDEX_REQUEST_TIMEOUT", str(REQUEST_TIMEOUT)))
    retrieval_timeout = float(
        os.getenv("PAGEINDEX_RETRIEVAL_TIMEOUT", str(RETRIEVAL_TIMEOUT))
    )
    poll_interval = float(os.getenv("PAGEINDEX_POLL_INTERVAL", str(POLL_INTERVAL)))
    if request_timeout <= 0 or retrieval_timeout <= 0 or poll_interval < 0:
        raise ValueError("PageIndex timeout values must be positive")
    return api_key, base_url, request_timeout, retrieval_timeout, poll_interval


def _request_json(
    method: str,
    endpoint: str,
    *,
    api_key: str,
    base_url: str,
    timeout: float,
    **kwargs: Any,
) -> dict[str, Any]:
    """Send one bounded PageIndex request and require a JSON object response."""
    response = requests.request(
        method,
        f"{base_url}{endpoint}",
        headers={"api_key": api_key},
        timeout=timeout,
        **kwargs,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("PageIndex returned a non-object JSON response")
    return payload


def _empty_cache() -> dict[str, Any]:
    return {"version": 1, "documents": {}}


def _load_cache() -> dict[str, Any]:
    if not CACHE_PATH.exists():
        return _empty_cache()
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.warn(f"Ignoring invalid PageIndex cache: {exc}", RuntimeWarning)
        return _empty_cache()
    if isinstance(payload, dict) and "documents" not in payload and all(
        isinstance(source, str) and isinstance(doc_id, str)
        for source, doc_id in payload.items()
    ):
        # Backward-compatible with the simple ``source -> doc_id`` cache shape
        # used by early versions of the project template.
        return {
            "version": 1,
            "documents": {
                source: {"doc_id": doc_id} for source, doc_id in payload.items()
            },
        }
    if not isinstance(payload, dict) or not isinstance(payload.get("documents"), dict):
        warnings.warn("Ignoring PageIndex cache with an invalid schema", RuntimeWarning)
        return _empty_cache()
    return payload


def _save_cache(cache: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = CACHE_PATH.with_suffix(CACHE_PATH.suffix + ".tmp")
    temporary.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(CACHE_PATH)


def _content_digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _source_pdf(document: dict) -> Path:
    """Use an original legal PDF or create a Unicode PDF for Markdown input."""
    relative_source = Path(document["metadata"]["source"])
    if document["metadata"]["doc_type"] == "legal":
        original = LANDING_LEGAL_DIR / f"{relative_source.stem}.pdf"
        if original.is_file():
            return original

    try:
        from fpdf import FPDF
    except ImportError as exc:  # pragma: no cover - depends on local setup
        raise RuntimeError(
            "fpdf2 is required to convert standardized Markdown for PageIndex upload"
        ) from exc

    PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    output = PDF_CACHE_DIR / f"{document['id'].replace('/', '__')}.pdf"
    source_path = STANDARDIZED_DIR / relative_source
    if output.exists() and output.stat().st_mtime_ns >= source_path.stat().st_mtime_ns:
        return output

    font_candidates = (
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    )
    font_path = next((path for path in font_candidates if path.is_file()), None)
    if font_path is None:
        raise RuntimeError("No Unicode TrueType font found for Markdown-to-PDF conversion")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("Unicode", fname=str(font_path))
    pdf.add_page()
    pdf.set_font("Unicode", size=10)
    # Soft-wrap very long non-space strings (usually URLs) before multi_cell.
    printable = re.sub(r"(\S{90})(?=\S)", r"\1 ", document["content"])
    pdf.multi_cell(0, 5, text=printable)
    pdf.output(str(output))
    return output


def upload_documents() -> None:
    """Upload changed standardized documents and atomically cache document IDs.

    A failure for one document does not discard IDs already cached for the
    others. Running this function again skips every unchanged document.
    """
    api_key, base_url, request_timeout, _, _ = _settings()
    if not api_key:
        warnings.warn(
            "PAGEINDEX_API_KEY is not configured; skipping PageIndex upload",
            RuntimeWarning,
        )
        return

    cache = _load_cache()
    cached_documents = cache["documents"]
    failures: list[str] = []
    for document in load_documents():
        source = document["metadata"]["source"]
        digest = _content_digest(document["content"])
        cached = cached_documents.get(source)
        if (
            isinstance(cached, dict)
            and cached.get("doc_id")
            and cached.get("sha256") == digest
        ):
            continue

        try:
            pdf_path = _source_pdf(document)
            with pdf_path.open("rb") as file_handle:
                response = _request_json(
                    "POST",
                    "/doc/",
                    api_key=api_key,
                    base_url=base_url,
                    timeout=request_timeout,
                    files={"file": (pdf_path.name, file_handle, "application/pdf")},
                    data={"if_retrieval": "true"},
                )
            doc_id = response.get("doc_id")
            if not isinstance(doc_id, str) or not doc_id.strip():
                raise ValueError("PageIndex upload response is missing doc_id")
            cached_documents[source] = {
                "doc_id": doc_id,
                "sha256": digest,
                "title": document["metadata"]["title"],
                "doc_type": document["metadata"]["doc_type"],
                "url": document["metadata"]["url"],
            }
            _save_cache(cache)
        except Exception as exc:  # provider/conversion errors must not stop the batch
            failures.append(f"{source}: {exc}")

    if failures:
        warnings.warn(
            f"PageIndex could not upload {len(failures)} document(s): "
            + "; ".join(failures),
            RuntimeWarning,
        )


def _retrieve_document(
    doc_id: str,
    query: str,
    *,
    api_key: str,
    base_url: str,
    request_timeout: float,
    retrieval_timeout: float,
    poll_interval: float,
) -> dict[str, Any]:
    job = _request_json(
        "POST",
        "/retrieval/",
        api_key=api_key,
        base_url=base_url,
        timeout=request_timeout,
        json={"doc_id": doc_id, "query": query, "thinking": False},
    )
    retrieval_id = job.get("retrieval_id")
    if not isinstance(retrieval_id, str) or not retrieval_id.strip():
        raise ValueError("PageIndex retrieval response is missing retrieval_id")

    deadline = time.monotonic() + retrieval_timeout
    while time.monotonic() < deadline:
        result = _request_json(
            "GET",
            f"/retrieval/{retrieval_id}/",
            api_key=api_key,
            base_url=base_url,
            timeout=request_timeout,
        )
        status = str(result.get("status", "")).lower()
        if status == "completed":
            return result
        if status in {"failed", "error", "cancelled"}:
            raise RuntimeError(f"PageIndex retrieval ended with status={status}")
        if poll_interval:
            time.sleep(min(poll_interval, max(0.0, deadline - time.monotonic())))
    raise TimeoutError(f"PageIndex retrieval timed out for document {doc_id}")


def _walk_nodes(value: Any):
    if isinstance(value, list):
        for item in value:
            yield from _walk_nodes(item)
    elif isinstance(value, dict):
        yield value
        children = value.get("nodes") or value.get("children")
        if isinstance(children, (list, dict)):
            yield from _walk_nodes(children)


def _node_contents(node: dict[str, Any]) -> list[tuple[str, int | None, float | None]]:
    relevant = (
        node.get("relevant_contents")
        or node.get("relevant_content")
        or node.get("contents")
    )
    if relevant is None:
        relevant = [node]
    elif isinstance(relevant, (str, dict)):
        relevant = [relevant]
    if not isinstance(relevant, list):
        return []

    output: list[tuple[str, int | None, float | None]] = []
    for item in relevant:
        if isinstance(item, str):
            content, page, score = item.strip(), None, None
        elif isinstance(item, dict):
            content = str(
                item.get("relevant_content")
                or item.get("content")
                or item.get("text")
                or item.get("markdown")
                or ""
            ).strip()
            raw_page = item.get("page_index", item.get("page", item.get("page_idx")))
            try:
                page = int(raw_page) if raw_page is not None else None
            except (TypeError, ValueError):
                page = None
            raw_score = item.get("score", node.get("score"))
            try:
                score = float(raw_score) if raw_score is not None else None
            except (TypeError, ValueError):
                score = None
        else:
            continue
        if content:
            output.append((content, page, score))
    return output


def _parse_results(
    responses: list[tuple[dict[str, Any], dict[str, Any]]],
    top_k: int,
) -> list[dict]:
    candidates: dict[str, dict] = {}
    rank = 0
    for entry, response in responses:
        raw_nodes = response.get("retrieved_nodes", response.get("result", []))
        for node in _walk_nodes(raw_nodes):
            node_id = str(node.get("node_id", node.get("id", "node")))
            for content, page, explicit_score in _node_contents(node):
                rank += 1
                digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:12]
                item_id = (
                    f"pageindex::{entry['doc_id']}::{node_id}::"
                    f"{page if page is not None else 'na'}::{digest}"
                )
                score = explicit_score if explicit_score is not None else 1.0 / rank
                if not math.isfinite(score):
                    continue
                chunk_index = max(0, page - 1) if page is not None else rank - 1
                result = {
                    "id": item_id,
                    "content": content,
                    "score": float(score),
                    "metadata": {
                        "source": entry["source"],
                        "title": entry["title"],
                        "doc_type": entry["doc_type"],
                        "url": entry.get("url"),
                        "chunk_index": chunk_index,
                    },
                    "retrieval_method": "pageindex",
                }
                current = candidates.get(item_id)
                if current is None or result["score"] > current["score"]:
                    candidates[item_id] = result

    results = sorted(
        candidates.values(), key=lambda item: (-item["score"], item["id"])
    )[:top_k]
    validate_search_results(results, top_k=top_k, expected_method="pageindex")
    return results


def _cache_entries(cache: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for source, value in sorted(cache.get("documents", {}).items()):
        if not isinstance(value, dict) or not isinstance(value.get("doc_id"), str):
            continue
        entries.append(
            {
                "source": source,
                "doc_id": value["doc_id"],
                "title": str(value.get("title") or Path(source).stem.replace("_", " ")),
                "doc_type": value.get("doc_type")
                if value.get("doc_type") in {"legal", "news"}
                else ("legal" if source.startswith("legal/") else "news"),
                "url": value.get("url") if isinstance(value.get("url"), str) else None,
            }
        )
    return entries


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Retrieve PageIndex evidence, returning ``[]`` on provider failure."""
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        raise TypeError("top_k must be an integer")
    query = query.strip()
    if not query or top_k <= 0:
        return []

    try:
        api_key, base_url, request_timeout, retrieval_timeout, poll_interval = _settings()
        if not api_key:
            return []
        entries = _cache_entries(_load_cache())
        if not entries:
            return []

        def retrieve(entry: dict[str, Any]):
            try:
                response = _retrieve_document(
                    entry["doc_id"],
                    query,
                    api_key=api_key,
                    base_url=base_url,
                    request_timeout=request_timeout,
                    retrieval_timeout=retrieval_timeout,
                    poll_interval=poll_interval,
                )
                return (entry, response), None
            except Exception as exc:
                # One document may still be processing while others are ready.
                # Preserve usable evidence instead of failing the whole fallback.
                return None, f"{entry['source']}: {exc}"

        # executor.map preserves cache order, keeping rank fallback deterministic.
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(entries))) as executor:
            outcomes = list(executor.map(retrieve, entries))
        responses = [response for response, _ in outcomes if response is not None]
        failures = [failure for _, failure in outcomes if failure is not None]
        if failures:
            warnings.warn(
                f"PageIndex retrieval failed for {len(failures)} document(s): "
                + "; ".join(failures),
                RuntimeWarning,
            )
        return _parse_results(responses, top_k)
    except Exception as exc:
        warnings.warn(f"PageIndex fallback unavailable: {exc}", RuntimeWarning)
        return []


if __name__ == "__main__":
    upload_documents()
