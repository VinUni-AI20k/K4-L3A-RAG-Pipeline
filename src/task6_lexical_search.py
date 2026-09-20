"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""


import numpy as np
from rank_bm25 import BM25Okapi

from .task4_chunking_indexing import chunk_documents, load_documents

CORPUS: list[dict] = []
_BM25_CACHE: dict = {}


def _get_corpus() -> list[dict]:
    global CORPUS
    if not CORPUS:
        CORPUS = chunk_documents(load_documents())
    return CORPUS


def build_bm25_index(corpus: list[dict]) -> BM25Okapi:
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    tokenized = [item["content"].lower().split() for item in corpus]
    return BM25Okapi(tokenized)


def _get_or_build_index(corpus: list[dict]) -> BM25Okapi:
    cache_key = id(corpus)
    if cache_key not in _BM25_CACHE:
        _BM25_CACHE[cache_key] = build_bm25_index(corpus)
    return _BM25_CACHE[cache_key]


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    global CORPUS
    corpus = CORPUS if CORPUS else _get_corpus()
    if not corpus or not query.strip() or top_k <= 0:
        return []

    tokens = query.lower().split()
    if not tokens:
        return []

    bm25 = _get_or_build_index(corpus)
    scores = bm25.get_scores(tokens)
    indices = np.argsort(scores)[::-1]

    results = []
    for index in indices:
        score = float(scores[index])
        if score <= 0:
            continue
        item = corpus[index]
        clean_metadata = dict(item["metadata"])
        if "chunk_index" in clean_metadata:
            clean_metadata["chunk_index"] = int(clean_metadata["chunk_index"])
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": score,
            "metadata": clean_metadata,
            "retrieval_method": "bm25",
        })
        if len(results) >= top_k:
            break

    return results


if __name__ == "__main__":
    for result in lexical_search("test query", top_k=3):
        print(result)
