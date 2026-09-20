"""Task 7: rerank dense and lexical results with Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score. Công thức: RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.
"""

import math

from .contracts import validate_document, validate_search_results


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse ranked lists once and return contract-compatible hybrid results.

    Source scores are deliberately ignored because cosine similarity and BM25
    scores are not directly comparable. If an input list accidentally repeats
    an ID, only its best (first) rank in that list contributes to RRF.
    """
    if not isinstance(ranked_lists, list) or any(
        not isinstance(ranked_list, list) for ranked_list in ranked_lists
    ):
        raise TypeError("ranked_lists must be a list of result lists")
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        raise TypeError("top_k must be an integer")
    if not isinstance(k, int) or isinstance(k, bool):
        raise TypeError("k must be an integer")
    if k < 0:
        raise ValueError("k must be non-negative")
    if top_k <= 0:
        return []

    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    first_seen: dict[str, int] = {}
    encounter_order = 0

    for ranked_list in ranked_lists:
        seen_in_list: set[str] = set()
        for rank, item in enumerate(ranked_list, start=1):
            validate_document(item, require_chunk=True)
            item_id = item["id"]
            if item_id in seen_in_list:
                continue
            seen_in_list.add(item_id)

            contribution = 1.0 / (k + rank)
            scores[item_id] = scores.get(item_id, 0.0) + contribution
            if item_id not in items:
                items[item_id] = item
                first_seen[item_id] = encounter_order
                encounter_order += 1

    ranked_ids = sorted(
        scores,
        key=lambda item_id: (-scores[item_id], first_seen[item_id], item_id),
    )
    results: list[dict] = []
    for item_id in ranked_ids[:top_k]:
        source = items[item_id]
        result = {
            "id": source["id"],
            "content": source["content"],
            "score": float(scores[item_id]),
            "metadata": dict(source["metadata"]),
            "retrieval_method": "hybrid",
        }
        if not math.isfinite(result["score"]):  # defensive; formula is finite for k >= 0
            raise ValueError(f"Non-finite RRF score for result {item_id!r}")
        results.append(result)

    validate_search_results(results, top_k=top_k, expected_method="hybrid")
    return results


if __name__ == "__main__":
    print("Import rerank_rrf and pass dense/BM25 ranked lists to fuse them.")
