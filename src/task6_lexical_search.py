"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

import re

from .contracts import validate_search_results
from .task4_chunking_indexing import chunk_documents, load_documents


CORPUS: list[dict] = []


def _tokenize(text: str) -> list[str]:
    """Tách từ Unicode, giữ tiếng Việt và số trong nội dung SGK."""
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    from rank_bm25 import BM25L

    return BM25L([_tokenize(item["content"]) for item in corpus])


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    tokens = _tokenize(query)
    if top_k <= 0 or not tokens:
        return []

    corpus = CORPUS if CORPUS else chunk_documents(load_documents())
    if not corpus:
        return []
    scores = build_bm25_index(corpus).get_scores(tokens)
    ranked = sorted(range(len(corpus)), key=lambda index: (-float(scores[index]), corpus[index]["id"]))
    results = []
    for index in ranked:
        score = float(scores[index])
        if score <= 0:
            break
        item = corpus[index]
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": score,
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })
        if len(results) == top_k:
            break
    validate_search_results(results, top_k=top_k, expected_method="bm25")
    return results


if __name__ == "__main__":
    for result in lexical_search("động năng", top_k=3):
        print(result["id"], f"score={result['score']:.4f}")
