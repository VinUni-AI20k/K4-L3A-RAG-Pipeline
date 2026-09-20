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

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"


CACHE_FILE = Path(__file__).parent.parent / "data" / "pageindex_docs.json"


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    if not PAGEINDEX_API_KEY:
        print("PAGEINDEX_API_KEY not configured. Skipping upload.")
        return

    try:
        import pageindex

        client = pageindex.PageIndex(api_key=PAGEINDEX_API_KEY)
        doc_ids: dict[str, str] = {}
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                doc_ids = json.load(f)

        if STANDARDIZED_DIR.exists():
            for file_path in STANDARDIZED_DIR.glob("*.md"):
                if file_path.name in doc_ids:
                    continue
                try:
                    res = client.documents.create(file=str(file_path))
                    doc_ids[file_path.name] = res.id if hasattr(res, "id") else str(res)
                except Exception as ex:
                    print(f"Failed to upload {file_path.name}: {ex}")

        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(doc_ids, f, indent=2)
    except Exception as e:
        print(f"PageIndex upload failed: {e}")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if not PAGEINDEX_API_KEY:
        return []

    try:
        import pageindex

        client = pageindex.PageIndex(api_key=PAGEINDEX_API_KEY)
        doc_ids: dict[str, str] = {}
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                doc_ids = json.load(f)

        if not doc_ids:
            return []

        search_res = client.search(
            query=query,
            document_ids=list(doc_ids.values()),
            top_k=top_k,
        )

        results: list[dict] = []
        nodes = getattr(search_res, "results", []) or []
        for rank, node in enumerate(nodes[: max(top_k, 0)], 1):
            results.append({
                "id": getattr(node, "id", f"pageindex-{rank}"),
                "content": getattr(node, "text", str(node)),
                "score": float(getattr(node, "score", 1.0 / rank)),
                "metadata": {
                    "source": getattr(node, "source", "pageindex"),
                    "title": getattr(node, "title", "PageIndex Fallback"),
                    "doc_type": "fallback",
                    "url": getattr(node, "url", None),
                    "chunk_index": rank - 1,
                },
                "retrieval_method": "pageindex",
            })
        return results
    except Exception as e:
        print(f"PageIndex search error: {e}")
        return []


if __name__ == "__main__":
    upload_documents()
