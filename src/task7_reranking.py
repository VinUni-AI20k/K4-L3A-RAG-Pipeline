"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score. Công thức: RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.
"""


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse nhiều ranked lists và trả hybrid SearchResult."""
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, start=1):
            item_id = item["id"]
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            if item_id not in items:
                items[item_id] = item

    # Sắp xếp các item theo RRF score giảm dần
    ranked_ids = sorted(scores.keys(), key=lambda item_id: scores[item_id], reverse=True)

    results: list[dict] = []
    for item_id in ranked_ids[:top_k]:
        result = items[item_id].copy()
        result["score"] = scores[item_id]
        result["retrieval_method"] = "hybrid"
        results.append(result)

    return results


if __name__ == "__main__":
    mock_dense = [
        {"id": "chunk-0", "content": "IELTS Task 1 Criteria", "score": 0.85, "metadata": {"source": "a.md", "title": "A", "doc_type": "legal", "url": None, "chunk_index": 0}, "retrieval_method": "dense"},
        {"id": "chunk-1", "content": "Overview paragraph tips", "score": 0.72, "metadata": {"source": "b.md", "title": "B", "doc_type": "news", "url": None, "chunk_index": 1}, "retrieval_method": "dense"},
    ]
    mock_bm25 = [
        {"id": "chunk-1", "content": "Overview paragraph tips", "score": 4.5, "metadata": {"source": "b.md", "title": "B", "doc_type": "news", "url": None, "chunk_index": 1}, "retrieval_method": "bm25"},
        {"id": "chunk-2", "content": "Grammar range band 7", "score": 3.2, "metadata": {"source": "c.md", "title": "C", "doc_type": "legal", "url": None, "chunk_index": 2}, "retrieval_method": "bm25"},
    ]
    fused = rerank_rrf([mock_dense, mock_bm25], top_k=3, k=60)
    print("RRF fusion demo output:")
    for res in fused:
        print(f"ID: {res['id']}, Score: {res['score']:.6f}, Method: {res['retrieval_method']}")
