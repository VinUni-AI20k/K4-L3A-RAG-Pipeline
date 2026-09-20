"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""


import math
from typing import Optional
import numpy as np
from rank_bm25 import BM25Okapi

CORPUS: list[dict] = []

_cached_bm25: Optional[BM25Okapi] = None
_cached_corpus_key: Optional[tuple[int, int]] = None


class SafeBM25Okapi(BM25Okapi):
    """BM25Okapi dùng công thức Lucene IDF để tránh IDF=0 khi tập văn bản nhỏ."""

    def _calc_idf(self, nd):
        for word, freq in nd.items():
            self.idf[word] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    tokenized = [item["content"].lower().split() for item in corpus]
    return SafeBM25Okapi(tokenized)


def _get_corpus() -> list[dict]:
    """Lấy corpus chunks từ bộ nhớ, ChromaDB hoặc standardized docs."""
    global CORPUS
    if CORPUS:
        return CORPUS

    try:
        from .task4_chunking_indexing import get_collection

        coll = get_collection()
        data = coll.get(include=["documents", "metadatas"])
        if data and data.get("ids") and len(data["ids"]) > 0:
            CORPUS = [
                {
                    "id": item_id,
                    "content": doc,
                    "metadata": meta if meta is not None else {},
                }
                for item_id, doc, meta in zip(
                    data["ids"], data["documents"], data["metadatas"]
                )
            ]
            if CORPUS:
                return CORPUS
    except Exception:
        pass

    try:
        from .task4_chunking_indexing import chunk_documents, load_documents

        CORPUS = chunk_documents(load_documents())
    except Exception:
        pass

    return CORPUS


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    if not query.strip() or top_k <= 0:
        return []

    corpus = _get_corpus()
    if not corpus:
        return []

    global _cached_bm25, _cached_corpus_key
    corpus_key = (id(corpus), len(corpus))
    if _cached_bm25 is None or _cached_corpus_key != corpus_key:
        _cached_bm25 = build_bm25_index(corpus)
        _cached_corpus_key = corpus_key

    query_tokens = query.lower().split()
    if not query_tokens:
        return []

    scores = _cached_bm25.get_scores(query_tokens)
    indices = np.argsort(scores)[::-1]

    results = []
    for index in indices:
        score_val = float(scores[index])
        if score_val <= 0:
            continue
        item = corpus[index]
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": score_val,
            "metadata": item.get("metadata", {}),
            "retrieval_method": "bm25",
        })
        if len(results) >= top_k:
            break

    return results


if __name__ == "__main__":
    for result in lexical_search("đào tạo lái xe hạng B", top_k=3):
        print(result)

