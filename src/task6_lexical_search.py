"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

from rank_bm25 import BM25Okapi
import numpy as np

CORPUS: list[dict] = []
_BM25_INDEX = None
_CACHED_CORPUS_ID = None


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    # TODO: Tokenize và tạo BM25 index.
    tokenized = [item["content"].lower().split() for item in corpus]
    return BM25Okapi(tokenized)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    # TODO: Tính BM25 scores và map lại corpus.
    global CORPUS, _BM25_INDEX, _CACHED_CORPUS_ID
    if not CORPUS:
        try:
            from .task4_chunking_indexing import get_collection
            col = get_collection()
            data = col.get(include=["documents", "metadatas"])
            if data and data.get("ids"):
                CORPUS = [
                    {
                        "id": cid,
                        "content": doc,
                        "metadata": meta,
                    }
                    for cid, doc, meta in zip(data["ids"], data["documents"], data["metadatas"])
                ]
        except Exception:
            pass
        if not CORPUS:
            from .task4_chunking_indexing import chunk_documents, load_documents
            CORPUS = chunk_documents(load_documents())

    if _BM25_INDEX is None or _CACHED_CORPUS_ID != id(CORPUS):
        _BM25_INDEX = build_bm25_index(CORPUS)
        _CACHED_CORPUS_ID = id(CORPUS)

    bm25 = _BM25_INDEX
    scores = bm25.get_scores(query.lower().split())

    # Tie-breaker khi test corpus nhỏ khiến idf = 0
    tokens = set(query.lower().split())
    for idx, doc in enumerate(CORPUS):
        doc_tokens = set(doc["content"].lower().split())
        match_count = len(tokens & doc_tokens)
        scores[idx] += match_count * 1e-4

    indices = np.argsort(scores)[::-1][:top_k]
    results = []
    for index in indices:
        if scores[index] <= 0:
            continue
        item = CORPUS[index]
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