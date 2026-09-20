"""Deterministic Reciprocal Rank Fusion."""

def rerank_rrf(ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60) -> list[dict]:
    if top_k <= 0:
        return []
    scores, items, first_rank = {}, {}, {}
    for ranked_list in ranked_lists:
        seen = set()
        for rank, item in enumerate(ranked_list, 1):
            item_id = item["id"]
            if item_id in seen:
                continue
            seen.add(item_id)
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            first_rank[item_id] = min(first_rank.get(item_id, rank), rank)
            items.setdefault(item_id, item)
    ordered = sorted(scores, key=lambda x: (-scores[x], first_rank[x], x))
    return [{**items[item_id], "score": scores[item_id],
        "retrieval_method": "hybrid"} for item_id in ordered[:top_k]]
