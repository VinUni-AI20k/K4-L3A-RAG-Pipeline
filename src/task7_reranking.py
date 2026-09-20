"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score — hai thang điểm này không cùng đơn vị (cosine trong [0, 1], BM25 không
chặn trên), cộng thẳng thì bảng nào điểm to hơn sẽ át bảng kia. Công thức:
RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.
Task 9 lấy cosine score gốc từ danh sách dense cho việc đó.

Rerank bằng model (Jina/BGE) là tuỳ chọn; mục này chỉ làm RRF.
"""


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse nhiều ranked lists và trả hybrid SearchResult."""
    if top_k <= 0:
        return []

    scores: dict[str, float] = {}
    best_rank: dict[str, int] = {}
    items: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            item_id = item.get("id")
            if not item_id:
                continue
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            # Giữ bản đầu tiên thấy được để không phụ thuộc thứ tự bảng đầu vào.
            if item_id not in items:
                items[item_id] = item
                best_rank[item_id] = rank
            else:
                best_rank[item_id] = min(best_rank[item_id], rank)

    # Điểm bằng nhau thì ưu tiên chunk có hạng đơn lẻ tốt hơn, rồi tới id để
    # kết quả ổn định giữa các lần chạy.
    ranked_ids = sorted(
        scores,
        key=lambda item_id: (-scores[item_id], best_rank[item_id], item_id),
    )

    results = []
    for item_id in ranked_ids[:top_k]:
        source = items[item_id]
        results.append({
            "id": item_id,
            "content": source["content"],
            "score": scores[item_id],
            "metadata": dict(source["metadata"]),
            "retrieval_method": "hybrid",
        })
    return results


if __name__ == "__main__":
    import sys

    from .task5_semantic_search import semantic_search
    from .task6_lexical_search import lexical_search

    question = " ".join(sys.argv[1:]) or "band 7 lexical resource task 2"
    dense = semantic_search(question, top_k=10)
    bm25 = lexical_search(question, top_k=10)
    fused = rerank_rrf([dense, bm25], top_k=5)

    print(f"Query: {question}\n")
    for rank, result in enumerate(fused, 1):
        head = result["content"].split("\n", 1)[0]
        print(f"{rank}. rrf={result['score']:.4f}  {head[:88]}")
