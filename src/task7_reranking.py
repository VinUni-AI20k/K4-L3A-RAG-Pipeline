"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score. Công thức: RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.

-> Dùng Jina hoặc self host hoặc bất cứ công cụ nào bạn quen
"""

import os

from dotenv import load_dotenv


load_dotenv()

# Hằng số làm phẳng của paper RRF gốc (Cormack et al., 2009).
RRF_K = int(os.getenv("RRF_K") or 60)


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = RRF_K,
) -> list[dict]:
    """Fuse nhiều ranked lists và trả hybrid SearchResult.

    Mỗi document nhận 1 / (k + rank) từ từng danh sách nó xuất hiện, rank tính
    từ 1. Document nằm top ở cả dense lẫn BM25 (ví dụ điều khoản vừa khớp ngữ
    nghĩa vừa chứa mã ngành) được cộng dồn nên nổi lên đầu.

    Hằng số k làm phẳng chênh lệch giữa các hạng đầu: k càng lớn thì thứ hạng
    tuyệt đối càng ít chi phối, tránh để một danh sách áp đảo danh sách kia.
    """
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        seen: set[str] = set()
        for rank, item in enumerate(ranked_list, 1):
            item_id = item["id"]
            # Một ID trùng trong cùng một danh sách chỉ được tính ở rank tốt nhất.
            if item_id in seen:
                continue
            seen.add(item_id)
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            items.setdefault(item_id, item)

    ranked_ids = sorted(scores, key=lambda item_id: scores[item_id], reverse=True)

    results: list[dict] = []
    for item_id in ranked_ids[: max(top_k, 0)]:
        # Copy để không ghi đè score gốc của dense/BM25 mà Task 9 còn cần.
        result = dict(items[item_id])
        result["score"] = scores[item_id]
        result["retrieval_method"] = "hybrid"
        results.append(result)
    return results


# --- Bonus: reranker chuyên dụng để đối chứng với RRF ---------------------
# RRF chỉ biết THỨ HẠNG, không biết nội dung: hai chunk cùng hạng thì điểm bằng
# nhau dù một chunk trả lời thẳng câu hỏi còn chunk kia chỉ nhắc tới từ khoá.
# Cross-encoder đọc đồng thời (query, chunk) nên chấm được mức liên quan thật.

RERANK_MODEL = os.getenv("RERANK_MODEL") or "BAAI/bge-reranker-v2-m3"
RERANK_PROVIDER = (os.getenv("RERANK_PROVIDER") or "local").strip().lower()
JINA_API_KEY = os.getenv("JINA_API_KEY", "")

_cross_encoder = None


def _get_cross_encoder():
    """Nạp cross-encoder một lần rồi dùng lại (model ~2.2GB, nạp lại rất tốn)."""
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder

        _cross_encoder = CrossEncoder(RERANK_MODEL, max_length=512)
    return _cross_encoder


def _score_local(query: str, documents: list[str]) -> list[float]:
    model = _get_cross_encoder()
    return [float(score) for score in model.predict([(query, doc) for doc in documents])]


def _score_jina(query: str, documents: list[str]) -> list[float]:
    """Jina Reranker API, dùng khi máy chấm không tải nổi model local."""
    import requests

    response = requests.post(
        "https://api.jina.ai/v1/rerank",
        headers={"Authorization": f"Bearer {JINA_API_KEY}"},
        json={
            "model": os.getenv("JINA_RERANK_MODEL") or "jina-reranker-v2-base-multilingual",
            "query": query,
            "documents": documents,
            "top_n": len(documents),
        },
        timeout=20,
    )
    response.raise_for_status()
    scores = [0.0] * len(documents)
    for item in response.json().get("results", []):
        scores[item["index"]] = float(item.get("relevance_score", 0.0))
    return scores


def rerank_model(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """Chấm lại candidates bằng cross-encoder, giữ nguyên contract SearchResult.

    Lỗi model hay lỗi mạng không được làm sập pipeline: trả lại thứ tự cũ.
    """
    if not candidates:
        return []

    documents = [item["content"] for item in candidates]
    try:
        if RERANK_PROVIDER == "jina" and JINA_API_KEY.strip():
            scores = _score_jina(query, documents)
        else:
            scores = _score_local(query, documents)
    except Exception as error:
        print(f"[rerank] Model lỗi, giữ thứ tự RRF: {type(error).__name__}: {error}")
        return candidates[: max(top_k, 0)]

    reranked = []
    for item, score in zip(candidates, scores):
        result = dict(item)
        result["score"] = float(score)
        result["retrieval_method"] = "hybrid"
        reranked.append(result)

    reranked.sort(key=lambda item: item["score"], reverse=True)
    return reranked[: max(top_k, 0)]


if __name__ == "__main__":
    dense = [
        {"id": "legal/thong_tu_06.md::chunk-3", "content": "Đối tượng xét tuyển thẳng", "score": 0.71, "metadata": {"chunk_index": 3}, "retrieval_method": "dense"},
        {"id": "legal/thong_tu_06.md::chunk-9", "content": "Quy đổi chứng chỉ ngoại ngữ", "score": 0.64, "metadata": {"chunk_index": 9}, "retrieval_method": "dense"},
    ]
    bm25 = [
        {"id": "legal/thong_tu_06.md::chunk-9", "content": "Quy đổi chứng chỉ ngoại ngữ", "score": 8.2, "metadata": {"chunk_index": 9}, "retrieval_method": "bm25"},
        {"id": "news/05_diem_moi.md::chunk-1", "content": "IELTS 6.5 quy đổi điểm", "score": 5.1, "metadata": {"chunk_index": 1}, "retrieval_method": "bm25"},
    ]
    for item in rerank_rrf([dense, bm25], top_k=3):
        print(f"{item['score']:.6f}  {item['retrieval_method']:6s}  {item['id']}")
