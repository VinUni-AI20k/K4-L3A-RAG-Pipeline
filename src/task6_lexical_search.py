"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""


import math
from typing import Any

from rank_bm25 import BM25Okapi


class RobustBM25Okapi(BM25Okapi):
    """BM25Okapi với smoothed IDF log(1 + (N - n + 0.5) / (n + 0.5)).
    
    Tránh IDF = 0 khi corpus nhỏ hoặc từ xuất hiện ở 50% văn bản.
    """

    def _calc_idf(self, nd):
        for word, freq in nd.items():
            self.idf[word] = math.log(
                1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5)
            )


CORPUS: list[dict] = []
_bm25_index: Any = None
_indexed_corpus_id: int = 0


def _get_corpus() -> list[dict]:
    """Lấy corpus từ biến toàn cục hoặc nạp từ Task 4."""
    global CORPUS
    if not CORPUS:
        from .task4_chunking_indexing import chunk_documents, load_documents

        documents = load_documents()
        CORPUS = chunk_documents(documents)
    return CORPUS


def build_bm25_index(corpus: list[dict]) -> BM25Okapi:
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    tokenized = [item["content"].lower().split() for item in corpus]
    return RobustBM25Okapi(tokenized)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    global _bm25_index, _indexed_corpus_id

    if top_k <= 0 or not query or not query.strip():
        return []

    corpus = CORPUS if CORPUS else _get_corpus()
    if not corpus:
        return []

    corpus_id = id(corpus)
    if _bm25_index is None or _indexed_corpus_id != corpus_id:
        _bm25_index = build_bm25_index(corpus)
        _indexed_corpus_id = corpus_id

    tokens = query.lower().split()
    if not tokens:
        return []

    scores = _bm25_index.get_scores(tokens)

    scored_indices = [
        (idx, score) for idx, score in enumerate(scores) if score > 0
    ]
    scored_indices.sort(key=lambda x: x[1], reverse=True)

    results: list[dict] = []
    seen_ids = set()
    for idx, score in scored_indices[:top_k]:
        item = corpus[idx]
        item_id = item["id"]
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)

        metadata = dict(item.get("metadata", {}))
        if metadata.get("url") == "":
            metadata["url"] = None

        results.append({
            "id": item_id,
            "content": item["content"],
            "score": float(score),
            "metadata": metadata,
            "retrieval_method": "bm25",
        })

    return results


if __name__ == "__main__":
    import io
    import sys

    if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    for result in lexical_search("học phí Đại học Quốc gia", top_k=3):
        print(f"[{result['score']:.4f}] {result['id']} - {result['metadata'].get('title')}")
