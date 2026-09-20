"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score. Công thức: RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.

-> Dùng Jina hoặc self host hoặc bất cứ công cụ nào bạn quen
"""


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse nhiều ranked lists và trả hybrid SearchResult."""
    if k < 0:
        raise ValueError("RRF k must be non-negative")
    if top_k <= 0:
        return []
    scores = {}
    items = {}
    for ranked_list in ranked_lists:
        seen = set()
        for item in ranked_list:
            if item.get("retrieval_method") == "hybrid":
                raise ValueError("RRF input must not already be fused")
            item_id = item["id"]
            if item_id in seen:
                continue
            seen.add(item_id)
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + len(seen))
            items.setdefault(item_id, item)
    ranked_ids = sorted(scores, key=scores.get, reverse=True)
    return [
        {**items[item_id], "score": scores[item_id], "retrieval_method": "hybrid"}
        for item_id in ranked_ids[:top_k]
    ]


if __name__ == "__main__":
    print("RRF ready. Run the contract tests to verify fusion.")
