"""
Task 9 — Retrieval pipeline hoàn chỉnh.

Dense và BM25 được chạy trên cùng corpus. RRF chỉ chạy một lần.
Fallback được quyết định bằng cosine score gốc của dense retrieval.
"""

import os

from dotenv import load_dotenv

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import pageindex_search


load_dotenv()


def _read_score_threshold() -> float:
    raw_value = os.getenv("SCORE_THRESHOLD", "").strip()

    if not raw_value:
        return 0.3

    try:
        return float(raw_value)
    except ValueError:
        return 0.3


SCORE_THRESHOLD = _read_score_threshold()
DEFAULT_TOP_K = 5


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """
    Trả về dense, hybrid hoặc PageIndex SearchResult.

    PageIndex chỉ được gọi khi cosine score tốt nhất của dense retrieval thấp
    hơn score_threshold. Không dùng RRF score để quyết định fallback.
    """

    query = query.strip()

    if not query or top_k <= 0:
        return []

    candidate_k = top_k * 2

    dense_results = semantic_search(
        query,
        top_k=candidate_k,
    )
    lexical_results = lexical_search(
        query,
        top_k=candidate_k,
    )

    if use_reranking:
        # Chỉ fuse đúng một lần.
        primary_results = rerank_rrf(
            [dense_results, lexical_results],
            top_k=top_k,
        )
    else:
        # Dùng cho cấu hình A/B dense-only.
        primary_results = dense_results[:top_k]

    best_dense_score = (
        float(dense_results[0]["score"])
        if dense_results
        else 0.0
    )

    if best_dense_score < score_threshold:
        try:
            fallback_results = pageindex_search(
                query,
                top_k=top_k,
            )

            if fallback_results:
                return fallback_results[:top_k]

        except Exception:
            # Provider ngoài lỗi thì vẫn trả kết quả retrieval ban đầu.
            pass

    return primary_results[:top_k]


if __name__ == "__main__":
    results = retrieve("test query", top_k=3)

    for result in results:
        print(result)