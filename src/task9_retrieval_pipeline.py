"""Task 9: dense/BM25 retrieval, one RRF pass, and PageIndex fallback.

Luồng xử lý:
    1. Chạy semantic_search và lexical_search.
    2. Fuse hai danh sách bằng RRF đúng một lần.
    3. Lấy best cosine score gốc từ dense results.
    4. Nếu score dưới threshold, thử PageIndex fallback.
    5. Nếu fallback lỗi, trả hybrid results thay vì crash.

Không so sánh threshold với RRF score vì hai thang đo khác nhau.
"""

import math
import warnings

from .contracts import validate_search_results
from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import pageindex_search


SCORE_THRESHOLD = 0.3
DEFAULT_TOP_K = 5


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Return hybrid evidence, or PageIndex evidence when dense is uncertain.

    ``use_reranking=False`` is the dense-only baseline used for A/B evaluation.
    Regardless of mode, fallback is decided solely from the original dense
    cosine score—not BM25 or RRF scores.
    """
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        raise TypeError("top_k must be an integer")
    if not isinstance(score_threshold, (int, float)) or isinstance(
        score_threshold, bool
    ):
        raise TypeError("score_threshold must be numeric")
    if not math.isfinite(float(score_threshold)):
        raise ValueError("score_threshold must be finite")
    if not isinstance(use_reranking, bool):
        raise TypeError("use_reranking must be a boolean")

    query = query.strip()
    if not query or top_k <= 0:
        return []

    candidate_count = top_k * 2
    try:
        dense = semantic_search(query, top_k=candidate_count)
        validate_search_results(
            dense, top_k=candidate_count, expected_method="dense"
        )
    except Exception as exc:
        warnings.warn(f"Dense retrieval unavailable: {exc}", RuntimeWarning)
        dense = []

    if use_reranking:
        try:
            sparse = lexical_search(query, top_k=candidate_count)
            validate_search_results(
                sparse, top_k=candidate_count, expected_method="bm25"
            )
        except Exception as exc:
            warnings.warn(f"Lexical retrieval unavailable: {exc}", RuntimeWarning)
            sparse = []

        # This is deliberately the only RRF call in the entire pipeline.
        try:
            primary = rerank_rrf([dense, sparse], top_k=top_k)
            validate_search_results(
                primary, top_k=top_k, expected_method="hybrid"
            )
        except Exception as exc:
            warnings.warn(f"RRF unavailable; using dense results: {exc}", RuntimeWarning)
            primary = dense[:top_k]
    else:
        # Dense-only baseline: do not run BM25 or RRF.
        primary = dense[:top_k]

    best_dense_score = max(
        (float(item["score"]) for item in dense),
        default=float("-inf"),
    )
    if best_dense_score < float(score_threshold):
        try:
            fallback = pageindex_search(query, top_k=top_k)
            validate_search_results(
                fallback, top_k=top_k, expected_method="pageindex"
            )
            if fallback:
                return fallback
        except Exception as exc:
            warnings.warn(f"PageIndex fallback unavailable: {exc}", RuntimeWarning)

    validate_search_results(primary, top_k=top_k)
    return primary


if __name__ == "__main__":
    for result in retrieve("Điều kiện kinh doanh dịch vụ lữ hành", top_k=3):
        print(result)
