"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
"""

import os
import json
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
CACHE_PATH = Path(__file__).parent.parent / ".pageindex_ids.json"


def _read_cache() -> dict[str, str]:
    if not CACHE_PATH.exists():
        return {}
    try:
        value = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_cache(cache: dict[str, str]) -> None:
    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=True, indent=2), encoding="utf-8"
    )


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    if not PAGEINDEX_API_KEY:
        return

    from pageindex import PageIndexClient

    cache = _read_cache()
    client = PageIndexClient(PAGEINDEX_API_KEY)
    for path in sorted(LANDING_DIR.rglob("*.pdf")):
        source = path.relative_to(LANDING_DIR).as_posix()
        if source in cache:
            continue
        response = client.submit_document(str(path))
        document_id = response.get("doc_id")
        if document_id:
            cache[source] = str(document_id)
    _write_cache(cache)


def _extract_texts(value: object) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        texts = []
        for item in value:
            texts.extend(_extract_texts(item))
        return texts
    if isinstance(value, dict):
        texts = []
        for key in ("content", "text", "summary", "node_text", "answer"):
            texts.extend(_extract_texts(value.get(key)))
        if texts:
            return texts
        for item in value.values():
            texts.extend(_extract_texts(item))
        return texts
    return []


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if top_k <= 0 or not query.strip() or not PAGEINDEX_API_KEY:
        return []

    from pageindex import PageIndexClient

    upload_documents()
    cache = _read_cache()
    client = PageIndexClient(PAGEINDEX_API_KEY)
    results = []
    for source, document_id in cache.items():
        retrieval = client.submit_query(document_id, query)
        retrieval_id = retrieval.get("retrieval_id")
        if not retrieval_id:
            continue
        response = client.get_retrieval(retrieval_id)
        for index, content in enumerate(_extract_texts(response)):
            results.append({
                "id": f"pageindex:{document_id}:{index}",
                "content": content,
                "score": 1.0 / (len(results) + 1),
                "metadata": {
                    "source": source,
                    "title": Path(source).stem,
                    "doc_type": "legal" if "legal" in Path(source).parts else "news",
                    "url": None,
                    "chunk_index": index,
                },
                "retrieval_method": "pageindex",
            })
            if len(results) >= top_k:
                return results
    return results


if __name__ == "__main__":
    upload_documents()
