"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""


import json
import re
import sys

try:
    from .task4_chunking_indexing import BM25_CORPUS_PATH
except ImportError:  # Hỗ trợ chạy trực tiếp: python src/task6_lexical_search.py
    from task4_chunking_indexing import BM25_CORPUS_PATH


CORPUS: list[dict] = []


def tokenize(text: str) -> list[str]:
    """Tokenize Unicode đơn giản, phù hợp văn bản tiếng Việt."""
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


def load_corpus() -> list[dict]:
    """Đọc corpus chunks đã được Task 4 tạo."""
    if not BM25_CORPUS_PATH.exists():
        raise FileNotFoundError(
            f"BM25 corpus not found: {BM25_CORPUS_PATH}. "
            "Run task4_chunking_indexing.py first."
        )
    return json.loads(BM25_CORPUS_PATH.read_text(encoding="utf-8"))


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ corpus chunks của Task 4."""
    from rank_bm25 import BM25Okapi

    tokenized = [tokenize(item["content"]) for item in corpus]
    return BM25Okapi(tokenized)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    corpus = CORPUS or load_corpus()
    if not corpus or top_k <= 0:
        return []

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    bm25 = build_bm25_index(corpus)
    scores = bm25.get_scores(query_tokens)
    query_terms = set(query_tokens)

    # Với corpus rất nhỏ, IDF có thể bằng 0. Lọc theo token overlap thay
    # vì loại bỏ mọi kết quả có score bằng 0.
    matching_indices = [
        index
        for index, item in enumerate(corpus)
        if query_terms.intersection(tokenize(item["content"]))
    ]
    indices = sorted(
        matching_indices,
        key=lambda index: float(scores[index]),
        reverse=True,
    )[:top_k]

    return [
        {
            "id": corpus[index]["id"],
            "content": corpus[index]["content"],
            "score": max(0.0, float(scores[index])),
            "metadata": corpus[index]["metadata"],
            "retrieval_method": "bm25",
        }
        for index in indices
    ]


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for result in lexical_search("học phí tuyển sinh", top_k=3):
        print(result)
