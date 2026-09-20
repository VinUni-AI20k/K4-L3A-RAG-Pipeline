"""
Task 9 — Retrieval pipeline hoàn chỉnh.

Luồng xử lý:
    1. Chạy semantic_search và lexical_search.
    2. Fuse hai danh sách bằng RRF đúng một lần.
    3. (Tuỳ chọn, RERANKER_ENABLED=1) cross-encoder chấm lại 2×top_k ứng viên
       RRF rồi cắt top_k — xem Task 12. Reranker lỗi thì dùng kết quả RRF.
    4. Lấy best cosine score gốc từ dense results.
    5. Nếu score dưới threshold, thử PageIndex fallback.
    6. Nếu fallback lỗi hoặc rỗng, trả hybrid results thay vì crash.

Không so sánh threshold với RRF score vì hai thang đo khác nhau: cosine nằm
trong [0, 1] và phản ánh độ gần ngữ nghĩa; RRF chỉ là tổng nghịch đảo thứ hạng,
luôn ~0.03 bất kể query có liên quan hay không.

Threshold được hiệu chỉnh trên query in-domain và out-of-domain (xem
calibrate_threshold bên dưới). Đo trên corpus IELTS (bge-m3, 985 chunks) với
6 query hiệu chỉnh + 20 câu golden dataset và 6 câu out_of_domain.json:
    - in-domain top-1 thấp nhất  0.5907 (golden: 0.6309)
    - unrelated top-1 cao nhất   0.4714
nên chọn 0.53 ở giữa khoảng trống (0.47, 0.59), mỗi phía dư ~0.06.
Query near-domain (IELTS Listening/Speaking) đạt 0.65-0.73, không tách được
bằng cosine; trường hợp này để Task 10 safe refusal xử lý.

Chạy:
    python -m src.task9_retrieval_pipeline "câu hỏi"
    python -m src.task9_retrieval_pipeline --calibrate
"""

import os
import sys

from dotenv import load_dotenv

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import pageindex_search
from .task12_cross_encoder_rerank import rerank_cross_encoder


load_dotenv()


def _threshold_from_env(default: float) -> float:
    raw = os.getenv("SCORE_THRESHOLD", "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


SCORE_THRESHOLD = _threshold_from_env(0.53)
DEFAULT_TOP_K = 5
CANDIDATE_MULTIPLIER = 2   # lấy dư ứng viên cho RRF có chỗ gộp
# Bật cross-encoder sau RRF (Task 12). Tắt mặc định để contract test và config
# B của evaluation đo đúng "hybrid + RRF"; config C và .env của nhóm bật lên.
RERANKER_ENABLED = os.getenv("RERANKER_ENABLED", "0").strip().lower() in {"1", "true", "yes"}


def retrieve_detailed(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
    use_cross_encoder: bool | None = None,
) -> dict:
    """Như retrieve() nhưng kèm thông tin để UI/Task 10 giải thích kết quả.

    ``use_reranking`` bật RRF (hybrid); ``use_cross_encoder`` bật cross-encoder
    sau RRF, None thì theo RERANKER_ENABLED. Cross-encoder chỉ có tác dụng khi
    use_reranking=True.

    Trả về dict:
        results            list[SearchResult]
        retrieval_source   "hybrid" | "pageindex" | "none"
        best_dense_score   cosine gốc cao nhất của dense search
        reranked           bool — cross-encoder đã chấm lại kết quả
        reranker_error     str | None
        fallback_tried     bool
        fallback_error     str | None
    """
    if use_cross_encoder is None:
        use_cross_encoder = RERANKER_ENABLED
    use_cross_encoder = use_cross_encoder and use_reranking

    candidates = max(top_k * CANDIDATE_MULTIPLIER, top_k)
    dense = semantic_search(query, top_k=candidates)
    sparse = lexical_search(query, top_k=candidates)

    reranked = False
    reranker_error = None
    if use_reranking and use_cross_encoder:
        # RRF vẫn chạy một lần; chỉ lấy dư ứng viên để cross-encoder có chỗ chọn.
        fused = rerank_rrf([dense, sparse], top_k=candidates)
        try:
            hybrid = rerank_cross_encoder(query, fused, top_k=top_k)
            reranked = True
        except Exception as error:  # noqa: BLE001 - model/API ngoài, không được làm UI chết
            reranker_error = f"{type(error).__name__}: {error}"
            hybrid = fused[:top_k]
    elif use_reranking:
        hybrid = rerank_rrf([dense, sparse], top_k=top_k)
    else:
        hybrid = dense[:top_k]

    best_dense_score = dense[0]["score"] if dense else 0.0
    info = {
        "results": hybrid,
        "retrieval_source": "hybrid" if hybrid else "none",
        "best_dense_score": best_dense_score,
        "reranked": reranked,
        "reranker_error": reranker_error,
        "fallback_tried": False,
        "fallback_error": None,
    }

    if best_dense_score >= score_threshold:
        return info

    # Dense không tự tin: thử PageIndex. Provider ngoài có thể lỗi, chậm hoặc
    # chưa cấu hình; mọi trường hợp đều quay về hybrid, không được làm UI chết.
    info["fallback_tried"] = True
    try:
        fallback = pageindex_search(query, top_k=top_k)
    except Exception as error:  # noqa: BLE001 - provider ngoài, lỗi gì cũng phải sống
        info["fallback_error"] = f"{type(error).__name__}: {error}"
        return info

    if fallback:
        info["results"] = fallback[:top_k]
        info["retrieval_source"] = "pageindex"
    return info


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Trả về hybrid hoặc pageindex SearchResult."""
    return retrieve_detailed(query, top_k, score_threshold, use_reranking)["results"]


# --------------------------------------------------------------------------- #
# Hiệu chỉnh threshold
# --------------------------------------------------------------------------- #

IN_DOMAIN_QUERIES = [
    "How many words minimum for Writing Task 2?",
    "What is the difference between Task Achievement and Task Response?",
    "Band 6 coherence and cohesion requirements",
    "What does Band 7 require for Lexical Resource in Writing Task 2?",
    "How is the overall writing band score calculated from Task 1 and Task 2?",
    "What are common mistakes in IELTS Writing Task 2?",
]

OUT_OF_DOMAIN_QUERIES = [
    "How do I cook Vietnamese pho at home?",
    "What is the capital of Brazil?",
    "How to fix a Python ImportError?",
    "Best time to visit Japan for cherry blossoms",
    "What is the IELTS Speaking test format?",   # cùng miền IELTS, khác kỹ năng
]


def calibrate_threshold() -> None:
    """In best dense score cho query in/out-of-domain để chọn threshold."""
    rows = []
    for label, queries in (("IN ", IN_DOMAIN_QUERIES), ("OUT", OUT_OF_DOMAIN_QUERIES)):
        for query in queries:
            dense = semantic_search(query, top_k=1)
            score = dense[0]["score"] if dense else 0.0
            rows.append((label, score, query))
            print(f"{label}  {score:.4f}  {query}")

    in_scores = [s for l, s, _ in rows if l == "IN "]
    out_scores = [s for l, s, _ in rows if l == "OUT"]
    print(f"\nIn-domain  : min={min(in_scores):.4f}  mean={sum(in_scores)/len(in_scores):.4f}")
    print(f"Out-domain : max={max(out_scores):.4f}  mean={sum(out_scores)/len(out_scores):.4f}")
    low, high = max(out_scores), min(in_scores)
    if low < high:
        print(f"Khoảng trống: ({low:.4f}, {high:.4f}) -> gợi ý threshold {(low + high) / 2:.2f}")
    else:
        print("Hai nhóm chồng lấn; threshold nào cũng có sai số, chọn theo ưu tiên precision/recall.")
    print(f"Threshold hiện tại: {SCORE_THRESHOLD}")


if __name__ == "__main__":
    if "--calibrate" in sys.argv:
        calibrate_threshold()
    else:
        question = " ".join(a for a in sys.argv[1:]) or "band 7 lexical resource task 2"
        detail = retrieve_detailed(question, top_k=5)
        print(f"Query: {question}")
        print(
            f"source={detail['retrieval_source']}  best_dense={detail['best_dense_score']:.4f}"
            f"  reranked={detail['reranked']}  fallback_tried={detail['fallback_tried']}"
            f"  error={detail['reranker_error'] or detail['fallback_error']}\n"
        )
        for rank, result in enumerate(detail["results"], 1):
            head = result["content"].split("\n", 1)[0]
            print(f"{rank}. [{result['retrieval_method']}] {result['score']:.4f}  {head[:85]}")
