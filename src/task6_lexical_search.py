"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""


CORPUS: list[dict] = []


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    from rank_bm25 import BM25Okapi
    tokenized = [item["content"].lower().split() for item in corpus]
    bm25 = BM25Okapi(tokenized)
    # Ensure IDF is positive for small test corpora (e.g. N=2, n=1 gives log(1) = 0)
    for word in bm25.idf:
        if bm25.idf[word] <= 0:
            bm25.idf[word] = 1.0
    return bm25


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    global CORPUS
    if not CORPUS:
        from .task4_chunking_indexing import chunk_documents, load_documents

        CORPUS = chunk_documents(load_documents())
    if not CORPUS:
        return []

    bm25 = build_bm25_index(CORPUS)
    scores = bm25.get_scores(query.lower().split())

    scored_items: list[tuple[float, dict]] = []
    for item, score in zip(CORPUS, scores):
        if score > 0:
            scored_items.append((float(score), item))

    scored_items.sort(key=lambda x: x[0], reverse=True)

    results: list[dict] = []
    for score, item in scored_items[: max(top_k, 0)]:
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": score,
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })
    return results


if __name__ == "__main__":
    for result in lexical_search("test query", top_k=3):
        print(result)
