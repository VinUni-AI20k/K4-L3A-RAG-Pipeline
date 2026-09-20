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
CACHE_FILE = Path(__file__).parent.parent / "data" / "pageindex_cache.json"


def upload_documents() -> dict[str, str]:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    if not PAGEINDEX_API_KEY:
        print("PAGEINDEX_API_KEY chưa được thiết lập trong .env.")
        return {}

    from pageindex import PageIndexClient

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    cache: dict[str, str] = {}
    if CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        rel_path = path.relative_to(STANDARDIZED_DIR).as_posix()
        if rel_path in cache:
            continue

        try:
            response = client.submit_document(file_path=str(path))
            doc_id = response.get("doc_id") or response.get("id")
            if doc_id:
                cache[rel_path] = doc_id
                print(f"Uploaded {rel_path} -> doc_id: {doc_id}")
        except Exception as e:
            print(f"Lỗi khi upload {rel_path}: {e}")

    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    return cache


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if not PAGEINDEX_API_KEY:
        raise RuntimeError("PAGEINDEX_API_KEY chưa được cấu hình trong .env.")

    if not CACHE_FILE.exists():
        upload_documents()

    try:
        cache: dict[str, str] = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        cache = {}

    if not cache:
        raise RuntimeError("Không tìm thấy document ID nào đã được upload lên PageIndex.")

    from pageindex import PageIndexClient

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)

    results: list[dict] = []
    for rel_path, doc_id in cache.items():
        if len(results) >= top_k:
            break
        try:
            res = client.submit_query(doc_id=doc_id, query=query)
            nodes = (
                res.get("nodes")
                or res.get("results")
                or res.get("retrieved_nodes")
                or []
            )
            for rank, node in enumerate(nodes):
                content = node.get("content") or node.get("text") or str(node)
                score = float(node.get("score", 1.0 / (rank + 1)))
                node_id = node.get("id") or f"{doc_id}::node-{rank}"
                results.append({
                    "id": str(node_id),
                    "content": content,
                    "score": score,
                    "metadata": {
                        "source": Path(rel_path).name,
                        "title": Path(rel_path).stem,
                        "doc_type": "legal" if "legal" in rel_path else "news",
                        "url": None,
                        "chunk_index": rank,
                    },
                    "retrieval_method": "pageindex",
                })
        except Exception as e:
            print(f"Lỗi khi query doc_id {doc_id} trên PageIndex: {e}")

    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    upload_documents()

