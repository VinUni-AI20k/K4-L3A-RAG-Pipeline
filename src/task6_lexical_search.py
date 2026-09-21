"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

from __future__ import annotations

import sys

import numpy as np
from rank_bm25 import BM25Plus

# CORPUS được lazy-load lần đầu gọi lexical_search() hoặc set từ bên ngoài
# (monkeypatch trong test). Không import task4 ở top-level để tránh circular import
# và tránh load embedding model khi chỉ cần lexical search.
CORPUS: list[dict] = []


def _load_corpus_if_empty() -> None:
    """Load corpus từ task4 nếu CORPUS chưa được set."""
    global CORPUS
    if CORPUS:
        return
    from src.task4_chunking_indexing import chunk_documents, load_documents
    documents = load_documents()
    CORPUS = chunk_documents(documents)


def build_bm25_index(corpus: list[dict]) -> BM25Plus:
    """Tạo BM25+ index từ cùng corpus chunks của Task 4.

    Dùng BM25Plus thay vì BM25Okapi vì BM25Plus không sinh IDF âm —
    docs không chứa query term luôn score = 0, docs chứa luôn score > 0,
    kể cả với corpus nhỏ.
    """
    if not corpus:
        raise ValueError("[task6] Corpus rỗng — chạy task4 để tạo chunks trước.")
    tokenized = [item["content"].lower().split() for item in corpus]
    return BM25Plus(tokenized)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    # Đọc CORPUS từ module globals — monkeypatch của pytest thay thế attribute
    # trên module object nên cần đọc qua sys.modules để luôn lấy giá trị mới nhất.
    module = sys.modules[__name__]
    corpus: list[dict] = module.CORPUS

    if not corpus:
        _load_corpus_if_empty()
        corpus = module.CORPUS

    if not corpus:
        print("[task6] Cảnh báo: corpus rỗng, trả về danh sách rỗng.")
        return []

    bm25 = build_bm25_index(corpus)
    scores = bm25.get_scores(query.lower().split())

    # Sort theo score giảm dần, lấy top_k.
    # Không filter score <= 0: BM25Okapi có thể trả score = 0 khi từ xuất hiện
    # trong toàn bộ corpus (IDF = 0), nhưng thứ hạng vẫn có nghĩa cho corpus nhỏ.
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        score = float(scores[idx])
        if score <= 0:
            break  # BM25Plus: docs không chứa query term = 0, đã sort nên break an toàn
        item = corpus[idx]
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": score,
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })
    return results


if __name__ == "__main__":
    results = lexical_search("hợp đồng mua bán", top_k=3)
    if results:
        for r in results:
            print(f"[{r['score']:.4f}] {r['id']}")
            print(f"  {r['content'][:120]}...")
    else:
        print("Không tìm thấy kết quả.")
