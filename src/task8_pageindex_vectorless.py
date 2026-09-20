"""Task 8 — PageIndex vectorless fallback.

Mục tiêu:
- nếu dense retrieval không đủ tín hiệu, hệ thống vẫn có thể tìm kiếm bằng
  tri thức theo trang (page-based) mà không làm crash pipeline.
- Khi không có API PageIndex thật, pipeline vẫn chạy bằng fallback cục bộ trên
  corpus Markdown đã chuẩn hóa.
"""

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
ROOT_DIR = Path(__file__).resolve().parent.parent
STANDARDIZED_DIR = ROOT_DIR / "data" / "standardized"
CACHE_PATH = ROOT_DIR / ".pageindex_cache.json"


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[\u2010-\u2015\-_/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"[\w\u00C0-\u1EF9]+", _normalize_text(text)) if token]


def _page_documents() -> list[dict[str, Any]]:
    if not STANDARDIZED_DIR.exists():
        return []

    docs: list[dict[str, Any]] = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not content:
            continue
        doc_type = "legal" if "legal" in path.parts else "news"
        docs.append(
            {
                "id": path.relative_to(ROOT_DIR).as_posix(),
                "content": content,
                "metadata": {
                    "source": path.name,
                    "title": path.stem,
                    "doc_type": doc_type,
                    "url": None,
                    "chunk_index": 0,
                },
            }
        )
    return docs


def _load_cache() -> dict[str, dict[str, Any]]:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache: dict[str, dict[str, Any]]) -> None:
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def upload_documents() -> None:
    """Warm up local cache and optionally attempt external PageIndex upload."""
    cache = _load_cache()
    docs = _page_documents()
    changed = False

    for doc in docs:
        if doc["id"] not in cache:
            cache[doc["id"]] = {
                "id": doc["id"],
                "source": doc["metadata"]["source"],
                "title": doc["metadata"]["title"],
                "doc_type": doc["metadata"]["doc_type"],
            }
            changed = True

    if changed:
        _save_cache(cache)

    if PAGEINDEX_API_KEY:
        try:
            module_name = "pageindex"
            __import__(module_name)
        except Exception:
            # Không crash dù không có SDK hoặc key không hợp lệ.
            return

    return None


def _local_pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Fallback cục bộ theo trang, không cần API ngoài."""
    if not query or not query.strip():
        return []

    query_tokens = set(_tokenize(query))
    if not query_tokens:
        return []

    results: list[dict[str, Any]] = []
    for doc in _page_documents():
        title = doc["metadata"]["title"]
        title_tokens = set(_tokenize(title))
        doc_tokens = _tokenize(doc["content"])

        title_score = sum(3 for token in query_tokens if token in title_tokens)
        content_score = sum(1 for token in query_tokens if token in doc_tokens)
        exact_phrase = 1.0 if _normalize_text(query) in _normalize_text(doc["content"]) else 0.0
        score = title_score + content_score + exact_phrase

        if score <= 0:
            continue

        results.append(
            {
                "id": doc["id"],
                "content": doc["content"][:5000],
                "score": float(score),
                "metadata": {
                    **doc["metadata"],
                    "page_path": doc["id"],
                },
                "retrieval_method": "pageindex",
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[: max(top_k, 1)]


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult. Nếu API ngoài không khả dụng, dùng fallback local."""
    upload_documents()

    if PAGEINDEX_API_KEY:
        try:
            try:
                from pageindex import PageIndexClient  # type: ignore
            except Exception:
                PageIndexClient = None

            if PageIndexClient is not None:
                client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
                response = client.search(query=query, top_k=top_k)
                items = response.get("results", []) if isinstance(response, dict) else response
                parsed: list[dict] = []
                for index, item in enumerate(items[:top_k]):
                    if isinstance(item, dict):
                        content = item.get("content") or item.get("text") or ""
                        metadata = dict(item.get("metadata", {}))
                        if not metadata:
                            metadata = {
                                "source": item.get("source") or "pageindex",
                                "title": item.get("title") or "PageIndex result",
                                "doc_type": "news",
                                "url": None,
                                "chunk_index": 0,
                            }
                        parsed.append(
                            {
                                "id": str(item.get("id") or f"pageindex-{index}"),
                                "content": str(content),
                                "score": float(item.get("score", max(0.0, 1.0 - index * 0.05))),
                                "metadata": metadata,
                                "retrieval_method": "pageindex",
                            }
                        )
                if parsed:
                    return parsed
        except Exception:
            # Bỏ qua lỗi API và dùng fallback local để không làm crash pipeline.
            pass

    return _local_pageindex_search(query, top_k=top_k)


if __name__ == "__main__":
    upload_documents()
    print(pageindex_search("quy định khiếu nại", top_k=3))
