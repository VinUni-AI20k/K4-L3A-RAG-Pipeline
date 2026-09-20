"""Task 9 ? Retrieval pipeline ho?n ch?nh.

Lu?ng x? l?:
    1. Ch?y semantic_search v? lexical_search.
    2. Fuse hai danh s?ch b?ng RRF ??ng m?t l?n.
    3. L?y best cosine score g?c t? dense results.
    4. N?u score d??i threshold, th? PageIndex fallback.
    5. N?u fallback l?i, tr? hybrid results thay v? crash.

Kh?ng so s?nh threshold v?i RRF score v? hai thang ?o kh?c nhau.
"""

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
    """Tr? v? hybrid ho?c pageindex SearchResult."""
    dense = semantic_search(query, top_k=top_k * 2)
    sparse = lexical_search(query, top_k=top_k * 2)

    hybrid = (
        rerank_rrf([dense, sparse], top_k=top_k)
        if use_reranking
        else dense[:top_k]
    )

    best_dense_score = dense[0]["score"] if dense else 0.0
    if best_dense_score < score_threshold:
        try:
            fallback = pageindex_search(query, top_k=top_k)
            if fallback:
                return fallback
        except Exception:
            # PageIndex/provider l?i ???c quy ??nh ph?i survivable.
            pass

    if not hybrid and dense:
        # RRF c? th? kh?ng tr? k?t qu? n?u c? hai nh?nh r?ng; tuy nhi?n n?u
        # dense c? k?t qu? nh?ng fusion r?ng th? gi? dense ?? pipeline ?n ??nh.
        return dense[:top_k]

    return hybrid[:top_k]


if __name__ == "__main__":
    for result in retrieve("V?nh H? Long", top_k=3):
        print(result["score"], result["metadata"]["title"])
