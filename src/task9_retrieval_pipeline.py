"""
Task 9 — Retrieval pipeline hoàn chỉnh.

Luồng xử lý:
    1. Chạy semantic_search và lexical_search.
    2. Fuse hai danh sách bằng RRF đúng một lần.
    3. Lấy best cosine score gốc từ dense results.
    4. Nếu score dưới threshold, thử PageIndex fallback.
    5. Nếu fallback lỗi, trả hybrid results thay vì crash.

Không so sánh threshold với RRF score vì hai thang đo khác nhau.
"""

import logging
import os

from dotenv import load_dotenv

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import PageIndexUnavailable, pageindex_search


load_dotenv()
logger = logging.getLogger(__name__)

# Hiệu chỉnh bằng `python -m src.calibrate_threshold` (bge-m3, cosine gốc của dense):
# in-domain min 0.618, out-of-domain max 0.447 → điểm giữa 0.53. Chi tiết:
# group_project/evaluation/threshold_calibration.json. SCORE_THRESHOLD trong .env
# (nếu có) ghi đè giá trị này.
CALIBRATED_THRESHOLD = 0.53
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD") or CALIBRATED_THRESHOLD)
DEFAULT_TOP_K = 5
CANDIDATE_MULTIPLIER = 3


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Trả về hybrid (hoặc dense nếu use_reranking=False) hay pageindex SearchResult."""
    candidates = top_k * CANDIDATE_MULTIPLIER
    dense = semantic_search(query, top_k=candidates)
    if use_reranking:
        sparse = lexical_search(query, top_k=candidates)
        ranked = rerank_rrf([dense, sparse], top_k=top_k)
    else:
        ranked = dense[:top_k]

    best_dense_score = dense[0]["score"] if dense else 0.0
    if best_dense_score < score_threshold:
        try:
            fallback = pageindex_search(query, top_k=top_k)
            if fallback:
                return fallback[:top_k]
        except PageIndexUnavailable as error:
            logger.debug("PageIndex fallback not configured: %s", error)
        except Exception as error:
            logger.warning("PageIndex fallback failed: %s", error)
    return ranked[:top_k]


def best_dense_score(query: str) -> float:
    """Cosine cao nhất của dense search — dùng cho calibrate và safe refusal."""
    dense = semantic_search(query, top_k=1)
    return dense[0]["score"] if dense else 0.0


if __name__ == "__main__":
    for result in retrieve("Người mua có bao nhiêu ngày để yêu cầu trả hàng?", top_k=3):
        print(f"{result['retrieval_method']} {result['score']:.4f} {result['id']}")
