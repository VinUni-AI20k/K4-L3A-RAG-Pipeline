"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""


CORPUS: list[dict] = []
_BM25_INDEX = None
_CACHED_LEN = 0


def get_corpus() -> list[dict]:
    """Lấy danh sách chunks, tự động nạp từ Task 4 nếu CORPUS chưa có."""
    global CORPUS
    if not CORPUS:
        from .task4_chunking_indexing import chunk_documents, load_documents

        CORPUS = chunk_documents(load_documents())
    return CORPUS


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    from rank_bm25 import BM25Plus

    tokenized = [item["content"].lower().split() for item in corpus]
    return BM25Plus(tokenized)


def get_bm25_index(corpus: list[dict]):
    global _BM25_INDEX, _CACHED_LEN
    if _BM25_INDEX is None or len(corpus) != _CACHED_LEN:
        _BM25_INDEX = build_bm25_index(corpus)
        _CACHED_LEN = len(corpus)
    return _BM25_INDEX


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    import numpy as np

    corpus = CORPUS if CORPUS else get_corpus()
    if not corpus:
        return []

    bm25 = get_bm25_index(corpus)
    scores = bm25.get_scores(query.lower().split())
    indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for index in indices:
        if scores[index] <= 0:
            continue
        item = corpus[index]
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": float(scores[index]),
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })

    return results


if __name__ == "__main__":
    for result in lexical_search("test query", top_k=3):
        print(result)
