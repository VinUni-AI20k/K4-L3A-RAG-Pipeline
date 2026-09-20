"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

from rank_bm25 import BM25Okapi
import numpy as np


CORPUS: list[dict] = []


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    tokenized = [item["content"].lower().split() for item in corpus]
    bm25 = BM25Okapi(tokenized)
    # Đảm bảo các từ xuất hiện trong corpus luôn có IDF dương để không bị score 0 khi corpus nhỏ
    for word, val in bm25.idf.items():
        if val <= 0:
            bm25.idf[word] = 0.5
    return bm25


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    global CORPUS
    if not CORPUS:
        from .task4_chunking_indexing import load_documents, chunk_documents
        CORPUS = chunk_documents(load_documents())

    if not CORPUS or not query or not query.strip():
        return []

    tokens = query.lower().split()
    if not tokens:
        return []

    bm25 = build_bm25_index(CORPUS)
    scores = bm25.get_scores(tokens)

    indices = np.argsort(scores)[::-1]

    results = []
    seen_ids = set()

    for idx in indices:
        score = float(scores[idx])
        if score <= 0:
            continue
        item = CORPUS[idx]
        if item["id"] in seen_ids:
            continue

        seen_ids.add(item["id"])
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": score,
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })

        if len(results) >= top_k:
            break

    return results


if __name__ == "__main__":
    test_query = "IELTS Writing"
    print(f"Executing lexical search for query: '{test_query}'")
    for r in lexical_search(test_query, top_k=3):
        print(f"- [{r['score']:.4f}] {r['id']} ({r['metadata']['title']})")
