"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score. Công thức: RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.
"""

from __future__ import annotations


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse nhiều ranked lists và trả hybrid SearchResult."""
    if top_k <= 0 or not ranked_lists:
        return []

    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    first_seen: dict[str, int] = {}
    order = 0

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list or [], 1):
            item_id = item["id"]
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            # Giữ bản ghi đầu tiên: dense đứng trước nên content/metadata của nó
            # được ưu tiên, và ID không bị trùng lặp trong output.
            if item_id not in items:
                items[item_id] = item
                first_seen[item_id] = order
                order += 1

    ranked_ids = sorted(scores, key=lambda item_id: (-scores[item_id], first_seen[item_id]))
    results: list[dict] = []
    for item_id in ranked_ids[:top_k]:
        result = dict(items[item_id])
        result["metadata"] = dict(items[item_id]["metadata"])
        result["score"] = scores[item_id]
        result["retrieval_method"] = "hybrid"
        results.append(result)
    return results


if __name__ == "__main__":
    from .task5_semantic_search import semantic_search
    from .task6_lexical_search import lexical_search

    query = "quy hoạch hệ thống du lịch Việt Nam"
    for result in rerank_rrf(
        [semantic_search(query, top_k=10), lexical_search(query, top_k=10)], top_k=3
    ):
        print(result["id"], round(result["score"], 5), result["metadata"]["title"])
