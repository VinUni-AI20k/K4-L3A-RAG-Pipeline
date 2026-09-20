"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score. Công thức: RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.
"""


import copy
import sys


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
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            if item_id not in items:
                items[item_id] = item

    ranked_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    results = []
    for item_id in ranked_ids[:top_k]:
        result = copy.deepcopy(items[item_id])
        result["score"] = scores[item_id]
        result["retrieval_method"] = "hybrid"
        results.append(result)

    return results


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    from src.task5_semantic_search import semantic_search
    from src.task6_lexical_search import lexical_search

    query = "VAMC xử lý nợ xấu như thế nào"
    dense_results = semantic_search(query, top_k=5)
    sparse_results = lexical_search(query, top_k=5)
    fused = rerank_rrf([dense_results, sparse_results], top_k=3)
    print(f"=== Hybrid RRF for: '{query}' ===")
    for res in fused:
        print(f"- [{res['score']:.6f}] {res['id']}: {res['content'][:80]}...")

