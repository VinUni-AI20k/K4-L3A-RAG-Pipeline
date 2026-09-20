"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

import re
import unicodedata
from functools import lru_cache

from .task4_chunking_indexing import get_collection


CORPUS: list[dict] = []


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold())


@lru_cache(maxsize=1)
def _cached_index(contents: tuple[str, ...]):
    from rank_bm25 import BM25Plus

    tokenized = [_tokenize(content) for content in contents]
    if not any(tokenized):
        return None
    # Positive IDF keeps exact matches useful even for a one-document corpus.
    return BM25Plus(tokenized, delta=0)


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    return _cached_index(tuple(item["content"] for item in corpus))


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    tokens = _tokenize(query)
    if top_k <= 0 or not tokens:
        return []
    corpus = CORPUS
    if not corpus:
        response = get_collection().get(include=["documents", "metadatas"])
        corpus = [
            {"id": item_id, "content": content, "metadata": {"url": None, **(metadata or {})}}
            for item_id, content, metadata in zip(
                response["ids"], response["documents"], response["metadatas"],
            )
        ]
    corpus = list({item["id"]: item for item in corpus}.values())
    bm25 = build_bm25_index(corpus)
    if bm25 is None:
        return []
    scores = bm25.get_scores(tokens)
    results = [
        {
            "id": item["id"], "content": item["content"], "score": float(score),
            "metadata": {"url": None, **item["metadata"]}, "retrieval_method": "bm25",
        }
        for item, score in zip(corpus, scores) if score > 0
    ]
    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    for result in lexical_search("test query", top_k=3):
        print(result)
