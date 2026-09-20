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
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            item_id = item["id"]
            scores[item_id] = scores.get(item_id, 0.0) + 1 / (k + rank)
            items[item_id] = item

    ranked_ids = sorted(scores, key=scores.get, reverse=True)
    results = []
    for item_id in ranked_ids[:top_k]:
        result = items[item_id].copy()
        result["score"] = scores[item_id]
        result["retrieval_method"] = "hybrid"
        results.append(result)
    return results


if __name__ == "__main__":
    # Demo: fuse sample dense and BM25 results
    _meta = lambda ci: {"source": "demo.md", "title": "Demo", "doc_type": "legal", "url": None, "chunk_index": ci}
    dense = [
        {"id": "chunk-0", "content": "Dense hit 1", "score": 0.9, "metadata": _meta(0), "retrieval_method": "dense"},
        {"id": "chunk-1", "content": "Dense hit 2", "score": 0.8, "metadata": _meta(1), "retrieval_method": "dense"},
    ]
    bm25 = [
        {"id": "chunk-1", "content": "BM25 hit 1", "score": 7.0, "metadata": _meta(1), "retrieval_method": "bm25"},
        {"id": "chunk-2", "content": "BM25 hit 2", "score": 5.0, "metadata": _meta(2), "retrieval_method": "bm25"},
    ]
    fused = rerank_rrf([dense, bm25], top_k=3, k=60)
    for r in fused:
        print(f"  {r['id']:>10}  score={r['score']:.6f}  method={r['retrieval_method']}")
