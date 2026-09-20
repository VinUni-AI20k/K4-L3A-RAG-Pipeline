"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""


import math
from rank_bm25 import BM25Okapi
import numpy as np


CORPUS: list[dict] = []


class StableBM25Okapi(BM25Okapi):
    """BM25Okapi với Lucene idf formula (tránh idf=0 trên toy corpus N=2)."""
    def _calc_idf(self, nd):
        for word, freq in nd.items():
            self.idf[word] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))


import re


def _tokenize(text: str) -> list[str]:
    """Tách từ làm sạch dấu câu, hỗ trợ cả tiếng Việt và tiếng Anh."""
    return re.findall(r"\w+", (text or "").lower())


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    tokenized = [_tokenize(item["content"]) for item in corpus]
    return StableBM25Okapi(tokenized)


def get_corpus() -> list[dict]:
    """Lấy corpus chunks (nếu CORPUS rỗng thì thử lấy từ ChromaDB)."""
    global CORPUS
    if CORPUS:
        return CORPUS
    try:
        from .task4_chunking_indexing import get_collection
        col = get_collection()
        data = col.get(include=["documents", "metadatas"])
        if data and data.get("ids"):
            CORPUS = [
                {"id": cid, "content": doc, "metadata": meta}
                for cid, doc, meta in zip(data["ids"], data["documents"], data["metadatas"])
            ]
    except Exception:
        pass
    return CORPUS


_CACHED_BM25 = None
_CACHED_CORPUS_KEY = None


def get_bm25_index(corpus: list[dict]):
    """Lấy hoặc tạo BM25 index có cache để tăng tốc độ truy vấn."""
    global _CACHED_BM25, _CACHED_CORPUS_KEY
    corpus_key = (id(corpus), len(corpus))
    if _CACHED_BM25 is not None and _CACHED_CORPUS_KEY == corpus_key:
        return _CACHED_BM25
    _CACHED_BM25 = build_bm25_index(corpus)
    _CACHED_CORPUS_KEY = corpus_key
    return _CACHED_BM25


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    corpus = CORPUS if CORPUS else get_corpus()
    if not corpus:
        return []

    tokenized_query = _tokenize(query)
    if not tokenized_query:
        return []

    bm25 = get_bm25_index(corpus)
    scores = bm25.get_scores(tokenized_query)
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
