"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
LANDING_LEGAL_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
CACHE_PATH = Path(__file__).parent.parent / "pageindex_doc_ids.json"
SUPPORTED_SUFFIXES = {".pdf", ".doc", ".docx"}


def _load_cache() -> dict[str, dict]:
    if not CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_cache(cache: dict[str, dict]) -> None:
    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _get_client():
    """Create the cloud client only when PageIndex is configured."""
    api_key = os.getenv("PAGEINDEX_API_KEY", PAGEINDEX_API_KEY).strip()
    if not api_key:
        return None
    try:
        from pageindex import PageIndexClient
    except ImportError as exc:
        raise RuntimeError("PageIndex SDK is not installed") from exc
    return PageIndexClient(index="cloud")


def _source_metadata(path: Path) -> dict:
    return {
        "source": path.name,
        "title": path.stem.replace("_", " ").replace("-", " ").title(),
        "doc_type": "legal",
        "url": None,
        "chunk_index": 0,
    }


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    client = _get_client()
    if client is None:
        return

    cache = _load_cache()
    if not LANDING_LEGAL_DIR.exists():
        return

    for path in sorted(LANDING_LEGAL_DIR.iterdir()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        source = path.name
        cached = cache.get(source, {})
        if cached.get("document_id"):
            continue

        response = client.submit_document(
            str(path), wait=True, metadata={"source": source, "doc_type": "legal"}
        )
        document_id = response.get("doc_id") if isinstance(response, dict) else None
        if not isinstance(document_id, str) or not document_id:
            raise RuntimeError(f"PageIndex did not return a document ID for {source}")
        cache[source] = {
            "document_id": document_id,
            "metadata": _source_metadata(path),
        }
        _save_cache(cache)


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if not query.strip() or top_k <= 0:
        return []

    client = _get_client()
    if client is None:
        return []
    cache = _load_cache()
    if not cache:
        return []

    results = []
    for source, cached in cache.items():
        document_id = cached.get("document_id")
        if not isinstance(document_id, str) or not document_id:
            continue
        # PageIndex returns a grounded answer with source citations.  That answer
        # is the most specific text exposed by the current SDK retrieval API.
        answer = client.chat(
            query,
            doc_id=document_id,
            citations=True,
            show_process=False,
        )
        if not isinstance(answer, str) or not answer.strip():
            continue
        metadata = cached.get("metadata") or {
            "source": source,
            "title": source,
            "doc_type": "legal",
            "url": None,
            "chunk_index": 0,
        }
        results.append(
            {
                "id": f"pageindex::{document_id}",
                "content": answer.strip(),
                "score": 1.0 / (len(results) + 1),
                "metadata": {**metadata, "chunk_index": 0},
                "retrieval_method": "pageindex",
            }
        )
        if len(results) >= top_k:
            break
    return results


if __name__ == "__main__":
    upload_documents()
