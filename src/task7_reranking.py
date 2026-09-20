"""Reciprocal Rank Fusion for dense and lexical result lists."""


def rerank_rrf(ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60) -> list[dict]:
    """Fuse rankings using ``sum(1 / (k + rank))`` and mark results hybrid."""
    if top_k <= 0:
        return []
    if k < 0:
        raise ValueError("k must be non-negative")
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    for ranked_list in ranked_lists:
        seen_in_list: set[str] = set()
        for rank, item in enumerate(ranked_list, start=1):
            item_id = item["id"]
            if item_id in seen_in_list:
                continue
            seen_in_list.add(item_id)
            scores[item_id] = scores.get(item_id, 0.0) + 1 / (k + rank)
            items.setdefault(item_id, item)
    return [{**items[item_id], "score": score, "retrieval_method": "hybrid"}
            for item_id, score in sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))[:top_k]]
