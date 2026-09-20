"""Task 7 ? Reciprocal Rank Fusion.

RRF g?p nhi?u b?ng x?p h?ng m? kh?ng c?ng tr?c ti?p cosine score v?i BM25
score. C?ng th?c: RRF(d) = sum(1 / (k + rank)), rank b?t ??u t? 1.

L?u ?: RRF score ch? ph?n ?nh th? h?ng, kh?ng d?ng ?? quy?t ??nh fallback.
"""


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse nhi?u ranked lists v? tr? hybrid SearchResult."""
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            item_id = item["id"]
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / float(k + rank)
            # L?y ph?n t? c? rank t?t nh?t; kh?ng quan tr?ng th? t? ngu?n ? ??y.
            if item_id not in items:
                items[item_id] = item

    ranked_ids = sorted(scores, key=scores.get, reverse=True)

    results = []
    for item_id in ranked_ids[:top_k]:
        result = items[item_id].copy()
        result["score"] = float(scores[item_id])
        result["retrieval_method"] = "hybrid"
        results.append(result)

    return results


if __name__ == "__main__":
    print("Implement rerank_rrf, then run contract tests.")
