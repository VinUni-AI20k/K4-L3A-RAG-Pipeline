"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5 (cùng hàm load + chunk của Task 4, nên cùng
ID), để Task 7 có thể gộp hai bảng xếp hạng theo ID. BM25 phù hợp với từ khóa
chính xác như "band 7", "150 words", "Task Achievement" — những thứ embedding
hay làm mờ. Output phải theo SearchResult và sort score giảm dần.

Chạy:
    python -m src.task6_lexical_search "câu hỏi"
"""

import os
import re
import sys

import numpy as np
from rank_bm25 import BM25Okapi


CORPUS: list[dict] = []

TOKEN = re.compile(r"\w+")

# Thêm token cặp liền kề ("band_7", "task_2") bên cạnh token đơn. Không có nó,
# "band 7 ... task 2" tách thành band/7/task/2 và tiền tố "Task 2 — Band 2" chứa
# "2" hai lần nên BM25 xếp Band 2/1/0 lên trên Band 7. Để dạng cờ để A/B.
BM25_BIGRAMS = os.getenv("BM25_BIGRAMS", "1") not in {"0", "false", "False"}

# Cache index theo corpus đang dùng; corpus khác (kể cả khi test monkeypatch)
# thì build lại. Build 1126 chunk mất < 1 giây nhưng gọi mỗi query thì lãng phí.
_index_cache: dict[tuple[int, int], tuple[BM25Okapi, list[set[str]]]] = {}


def tokenize(text: str) -> list[str]:
    """Hạ chữ thường, tách theo ký tự chữ/số ("task." khớp "task"), kèm bigram."""
    unigrams = TOKEN.findall(text.lower())
    if not BM25_BIGRAMS:
        return unigrams
    bigrams = [f"{a}_{b}" for a, b in zip(unigrams, unigrams[1:])]
    return unigrams + bigrams


def build_bm25_index(corpus: list[dict]) -> BM25Okapi:
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    return BM25Okapi([tokenize(item["content"]) for item in corpus])


def _load_default_corpus() -> list[dict]:
    from .task4_chunking_indexing import chunk_documents, load_documents

    return chunk_documents(load_documents())


def _get_index() -> tuple[list[dict], BM25Okapi | None, list[set[str]]]:
    global CORPUS
    if not CORPUS:
        CORPUS = _load_default_corpus()
    if not CORPUS:
        return CORPUS, None, []

    key = (id(CORPUS), len(CORPUS))
    if key not in _index_cache:
        _index_cache.clear()
        token_sets = [set(tokenize(item["content"])) for item in CORPUS]
        _index_cache[key] = (build_bm25_index(CORPUS), token_sets)
    bm25, token_sets = _index_cache[key]
    return CORPUS, bm25, token_sets


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    tokens = tokenize(query)
    if not tokens or top_k <= 0:
        return []

    corpus, bm25, token_sets = _get_index()
    if bm25 is None:
        return []

    query_terms = set(tokens)
    scores = bm25.get_scores(tokens)

    # Chỉ giữ chunk có ít nhất một từ khớp. Không lọc theo score > 0 vì với
    # corpus rất nhỏ, IDF của BM25Okapi có thể bằng 0 cho mọi từ và điểm về 0
    # ngay cả khi khớp từ; corpus lớn thì hai điều kiện tương đương.
    candidates = [
        index for index in np.argsort(scores)[::-1]
        if token_sets[index] & query_terms
    ][:top_k]

    results = []
    for index in candidates:
        score = float(scores[index])
        item = corpus[index]
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": score,
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })
    return results


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "band 7 lexical resource task 2"
    print(f"Query: {question}\n")
    for rank, result in enumerate(lexical_search(question, top_k=5), 1):
        head = result["content"].split("\n", 1)[0]
        print(f"{rank}. score={result['score']:.3f}  {head[:90]}")
        print(f"   source={result['metadata']['source']}")
