"""
Task 9 — Retrieval pipeline hoàn chỉnh.

Luồng xử lý:
    1. Chạy semantic_search và lexical_search.
    2. Fuse hai danh sách bằng RRF đúng một lần.
    3. Lấy best cosine score gốc từ dense results.
    4. Nếu score dưới threshold, thử PageIndex fallback.
    5. Nếu fallback lỗi, trả hybrid results thay vì crash.

Không so sánh threshold với RRF score vì hai thang đo khác nhau.
"""

import os

from dotenv import load_dotenv

from .contracts import validate_search_results
from .task4_chunking_indexing import ROOT
from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import pageindex_search


load_dotenv(ROOT / ".env")
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD") or "0.3")
DEFAULT_TOP_K = 5


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Trả về hybrid hoặc pageindex SearchResult."""
    if top_k <= 0 or not query.strip():
        return []
    if not 0 <= score_threshold <= 1:
        raise ValueError("score_threshold phải nằm trong [0, 1]")

    dense = semantic_search(query, top_k=top_k * 2)
    sparse = lexical_search(query, top_k=top_k * 2) if use_reranking else []
    hybrid = (
        rerank_rrf([dense, sparse], top_k=top_k)
        if use_reranking else dense[:top_k]
    )

    best_dense_score = dense[0]["score"] if dense else 0.0
    if best_dense_score < score_threshold:
        try:
            fallback = pageindex_search(query, top_k=top_k)
            if fallback:
                validate_search_results(fallback, top_k=top_k, expected_method="pageindex")
                return fallback
        except Exception:
            # PageIndex is optional; a transient remote error must not break retrieval.
            pass

    validate_search_results(hybrid, top_k=top_k)
    return hybrid


if __name__ == "__main__":
    for result in retrieve("động năng là gì", top_k=3):
        print(result["id"], result["retrieval_method"], f"score={result['score']:.4f}")
