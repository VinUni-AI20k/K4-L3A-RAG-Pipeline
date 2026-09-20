"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

from typing import Any

CORPUS: list[dict] = []


def _get_or_load_corpus() -> list[dict]:
    """Lấy CORPUS hiện tại hoặc nạp từ ChromaDB / standardized files nếu chưa nạp."""
    global CORPUS
    if CORPUS:
        return CORPUS

    # Thử lấy từ ChromaDB
    try:
        from .task4_chunking_indexing import get_collection
        collection = get_collection()
        data = collection.get(include=["documents", "metadatas"])
        if data and data.get("ids"):
            CORPUS = [
                {
                    "id": item_id,
                    "content": doc,
                    "metadata": meta,
                }
                for item_id, doc, meta in zip(
                    data["ids"], data["documents"], data["metadatas"]
                )
            ]
            return CORPUS
    except Exception:
        pass

    # Fallback: đọc trực tiếp từ standardized files
    try:
        from .task4_chunking_indexing import chunk_documents, load_documents
        CORPUS = chunk_documents(load_documents())
    except Exception:
        pass

    return CORPUS


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    from rank_bm25 import BM25Plus

    tokenized = [item["content"].lower().split() for item in corpus]
    return BM25Plus(tokenized)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    if not query or not query.strip():
        return []

    corpus = CORPUS if CORPUS else _get_or_load_corpus()
    if not corpus:
        return []

    import numpy as np

    bm25 = build_bm25_index(corpus)
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    indices = np.argsort(scores)[::-1]
    results = []
    for index in indices:
        if len(results) >= top_k:
            break
        score = float(scores[index])
        if score <= 0:
            continue
        item = corpus[index]
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": score,
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })

    return results


if __name__ == "__main__":
    test_query = "359/2026/NĐ-CP VAMC"
    print(f"=== Lexical search: '{test_query}' ===")
    for res in lexical_search(test_query, top_k=3):
        print(f"- [{res['score']:.4f}] {res['id']}: {res['content'][:100]}...")
