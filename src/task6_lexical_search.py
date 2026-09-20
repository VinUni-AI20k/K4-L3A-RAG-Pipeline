"""Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

import re

from .task4_chunking_indexing import chunk_documents, load_documents


CORPUS: list[dict] = []


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    from rank_bm25 import BM25Okapi

    return BM25Okapi([_tokenize(item["content"]) for item in corpus])


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


def _get_corpus() -> list[dict]:
    if CORPUS:
        return CORPUS
    try:
        return chunk_documents(load_documents())
    except NotImplementedError:
        return []


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    corpus = _get_corpus()
    tokens = _tokenize(query)
    if top_k <= 0 or not corpus or not tokens:
        return []

    scores = build_bm25_index(corpus).get_scores(tokens)
    ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
    results = []
    seen_ids = set()
    for index, score in ranked:
        item = corpus[index]
        overlap = set(tokens) & set(_tokenize(item["content"]))
        if not overlap or item["id"] in seen_ids:
            continue
        seen_ids.add(item["id"])
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": max(float(score), len(overlap) / len(tokens) * 1e-9),
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })
        if len(results) == top_k:
            break
    return results


if __name__ == "__main__":
    for result in lexical_search("test query", top_k=3):
        print(result)
