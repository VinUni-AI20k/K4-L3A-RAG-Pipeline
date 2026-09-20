"""
Task 12 (bonus) — Reranker nâng cao bằng cross-encoder.

RRF (Task 7) chỉ gộp thứ hạng, không đọc nội dung: chunk khớp từ khoá phổ biến
("Band", "Task 2") vẫn lọt top-5 dù không trả lời câu hỏi — đây là lý do
precision của hybrid thấp hơn dense-only 0.16 trong evaluation. Cross-encoder
đọc cặp (query, chunk) cùng lúc nên phân biệt được "có trả lời không" thay vì
chỉ "có giống không".

Vị trí trong pipeline (Task 9): dense + BM25 → RRF lấy 2×top_k ứng viên →
cross-encoder chấm lại → cắt top_k. RRF vẫn chạy đúng một lần; reranker chỉ
sắp xếp lại danh sách đã gộp, không thêm ứng viên mới.

Provider (RERANKER_PROVIDER trong .env):
    local   sentence-transformers CrossEncoder, mặc định BAAI/bge-reranker-v2-m3
            (cùng họ với bge-m3, hỗ trợ tiếng Việt). Score đã qua sigmoid, [0, 1].
    jina    Jina Reranker API, cần JINA_API_KEY.

Output giữ retrieval_method của input ("hybrid"); score là điểm cross-encoder,
sort giảm dần để đúng contract SearchResult. Score này không dùng cho fallback —
Task 9 vẫn quyết định bằng cosine gốc của dense trước khi rerank.

Chạy:
    python -m src.task12_cross_encoder_rerank "câu hỏi"   # so RRF và sau rerank
"""

import os
import sys
from functools import lru_cache

import requests
from dotenv import load_dotenv


load_dotenv()

RERANKER_PROVIDER = os.getenv("RERANKER_PROVIDER", "local").strip().lower() or "local"
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "").strip() or {
    "local": "BAAI/bge-reranker-v2-m3",
    "jina": "jina-reranker-v2-base-multilingual",
}.get(RERANKER_PROVIDER, "BAAI/bge-reranker-v2-m3")
RERANKER_DEVICE = os.getenv("RERANKER_DEVICE", "").strip() or os.getenv("EMBEDDING_DEVICE", "").strip() or None
# Cắt chunk dài để cross-encoder không tràn cửa sổ; bge-reranker-v2-m3 nhận 8192
# token nhưng chunk 500 ký tự của Task 4 còn xa ngưỡng này.
MAX_LENGTH = 1024
JINA_URL = "https://api.jina.ai/v1/rerank"
JINA_TIMEOUT = 30


@lru_cache(maxsize=1)
def _local_model():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(RERANKER_MODEL, device=RERANKER_DEVICE, max_length=MAX_LENGTH)


def score_pairs(query: str, passages: list[str]) -> list[float]:
    """Điểm liên quan của từng passage với query, cùng thứ tự với input."""
    if not passages:
        return []

    if RERANKER_PROVIDER == "local":
        scores = _local_model().predict([(query, passage) for passage in passages])
        return [float(score) for score in scores]

    if RERANKER_PROVIDER == "jina":
        api_key = os.getenv("JINA_API_KEY", "")
        if not api_key:
            raise ValueError("JINA_API_KEY is not configured")
        response = requests.post(
            JINA_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": RERANKER_MODEL,
                "query": query,
                "documents": passages,
                "top_n": len(passages),
                "return_documents": False,
            },
            timeout=JINA_TIMEOUT,
        )
        response.raise_for_status()
        scores = [0.0] * len(passages)
        for item in response.json().get("results", []):
            scores[int(item["index"])] = float(item["relevance_score"])
        return scores

    raise ValueError(f"Unsupported RERANKER_PROVIDER: {RERANKER_PROVIDER}")


def rerank_cross_encoder(query: str, results: list[dict], top_k: int = 5) -> list[dict]:
    """Chấm lại ``results`` bằng cross-encoder, trả top_k theo score giảm dần.

    Không thay đổi input; giữ id, content, metadata và retrieval_method của mỗi
    chunk, chỉ thay score. Điểm bằng nhau thì giữ thứ tự RRF ban đầu.
    """
    if top_k <= 0 or not results or not query.strip():
        return []

    scores = score_pairs(query, [item["content"] for item in results])
    order = sorted(range(len(results)), key=lambda index: (-scores[index], index))

    reranked = []
    for index in order[:top_k]:
        source = results[index]
        reranked.append({
            "id": source["id"],
            "content": source["content"],
            "score": scores[index],
            "metadata": dict(source["metadata"]),
            "retrieval_method": source["retrieval_method"],
        })
    return reranked


if __name__ == "__main__":
    from .task5_semantic_search import semantic_search
    from .task6_lexical_search import lexical_search
    from .task7_reranking import rerank_rrf

    question = " ".join(sys.argv[1:]) or "What does Band 7 require for Lexical Resource in Writing Task 2?"
    dense = semantic_search(question, top_k=10)
    bm25 = lexical_search(question, top_k=10)
    fused = rerank_rrf([dense, bm25], top_k=10)
    reranked = rerank_cross_encoder(question, fused, top_k=5)

    print(f"Query: {question}\n")
    print("RRF top-5:")
    for rank, item in enumerate(fused[:5], 1):
        print(f"  {rank}. rrf={item['score']:.4f}  {item['content'].split(chr(10), 1)[0][:80]}")
    print(f"\n{RERANKER_PROVIDER}/{RERANKER_MODEL} top-5:")
    for rank, item in enumerate(reranked, 1):
        before = next(i for i, f in enumerate(fused, 1) if f["id"] == item["id"])
        print(f"  {rank}. ce={item['score']:.4f}  (rrf #{before})  {item['content'].split(chr(10), 1)[0][:80]}")
