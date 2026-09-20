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

import os

from dotenv import load_dotenv

from .bonus_query_expansion import expand_query
from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_model, rerank_rrf
from .task8_pageindex_vectorless import pageindex_search


load_dotenv()

# Hiệu chỉnh bằng query in-domain và out-of-domain, xem báo cáo cá nhân.
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD") or 0.38)
DEFAULT_TOP_K = 5

# Lấy dư ứng viên cho RRF: mỗi nhánh giữ top_k * CANDIDATE_MULTIPLIER kết quả
# để chunk chỉ mạnh ở một nhánh vẫn có cơ hội được fuse lên.
CANDIDATE_MULTIPLIER = 2

# Bonus — bật bằng .env. Signature của retrieve() bị contract test khoá cứng ở
# 4 tham số nên hai tính năng này đi qua flag module, không thêm tham số mới.
# Để mặc định false: contract test phải chạy offline, không gọi LLM/model ngoài.
USE_HYDE = (os.getenv("USE_HYDE") or "false").strip().lower() == "true"
USE_MODEL_RERANK = (os.getenv("USE_MODEL_RERANK") or "false").strip().lower() == "true"


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Trả về hybrid hoặc pageindex SearchResult."""
    candidate_k = top_k * CANDIDATE_MULTIPLIER

    # HyDE chỉ đổi vector truy vấn, mọi thứ phía sau vẫn chạy trên query gốc.
    search_query = expand_query(query) if USE_HYDE else query

    dense = semantic_search(search_query, top_k=candidate_k)
    sparse = lexical_search(search_query, top_k=candidate_k)

    # RRF chỉ chạy đúng một lần trong toàn pipeline.
    if use_reranking:
        # Khi có cross-encoder thì fuse rộng hơn rồi mới cắt: chấm lại đúng
        # top_k chỉ đảo được thứ tự, không kéo nổi chunk tốt đang nằm hạng k+1.
        fused_k = candidate_k if USE_MODEL_RERANK else top_k
        hybrid = rerank_rrf([dense, sparse], top_k=fused_k)
        if USE_MODEL_RERANK:
            # Chấm trên câu hỏi GỐC: đoạn giả định của HyDE không phải thứ cần
            # khớp, câu hỏi thật mới là thứ cần khớp.
            hybrid = rerank_model(query, hybrid, top_k=top_k)
    else:
        hybrid = dense[:top_k]

    # Quyết định fallback dựa trên cosine similarity gốc của dense, không dùng
    # RRF score: RRF chỉ là thứ hạng (~0.016–0.033) nên không cùng thang đo.
    best_dense_score = dense[0]["score"] if dense else 0.0

    if best_dense_score < score_threshold:
        try:
            fallback = pageindex_search(query, top_k=top_k)
        except Exception as error:  # PageIndex là dịch vụ ngoài, không được sập UI.
            print(f"[task9] PageIndex fallback lỗi, dùng hybrid: {error}")
        else:
            if fallback:
                return fallback[:top_k]

    return hybrid[:top_k]


if __name__ == "__main__":
    import sys

    user_query = " ".join(sys.argv[1:]) or "Thí sinh được cộng bao nhiêu điểm ưu tiên khu vực?"
    print(f"Query: {user_query}\nSCORE_THRESHOLD={SCORE_THRESHOLD}\n")
    for item in retrieve(user_query, top_k=3):
        print(f"{item['score']:.6f}  {item['retrieval_method']:9s}  {item['id']}")
