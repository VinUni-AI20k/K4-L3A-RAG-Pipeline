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

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import pageindex_search


import os
from dotenv import load_dotenv

load_dotenv()

SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.3"))
DEFAULT_TOP_K = 5
ENABLE_QUERY_EXPANSION = os.getenv("ENABLE_QUERY_EXPANSION", "false").lower() in ("true", "1", "yes")

# Dictionary mở rộng từ đồng nghĩa phục vụ Query Expansion (Bonus +3)
SYNONYMS_DICT = {
    "bán hàng": ["mở bán", "giao dịch", "hợp đồng"],
    "ưu đãi": ["chiết khấu", "khuyến mại", "quà tặng"],
    "khiếu nại": ["phản ánh", "yêu cầu", "tranh chấp", "bảo vệ quyền lợi"],
    "bảo mật": ["bảo vệ", "dữ liệu cá nhân", "thông tin khách hàng"],
    "người cao tuổi": ["khách hàng dễ bị tổn thương", "ưu tiên"],
    "thanh toán": ["tiến độ", "trả góp", "lãi suất"],
}


def expand_query(query: str) -> list[str]:
    """Tạo các biến thể mở rộng cho query dựa trên từ đồng nghĩa."""
    expanded = [query]
    q_lower = query.lower()
    for key, syns in SYNONYMS_DICT.items():
        if key in q_lower:
            for syn in syns:
                if syn not in q_lower:
                    expanded.append(f"{query} {syn}")
    return expanded


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Trả về hybrid hoặc pageindex SearchResult."""
    dense = semantic_search(query, top_k=top_k * 2)

    if ENABLE_QUERY_EXPANSION:
        queries = expand_query(query)
        all_sparse = []
        for q in queries:
            all_sparse.extend(lexical_search(q, top_k=top_k * 2))
        seen = {}
        for item in all_sparse:
            if item["id"] not in seen or item["score"] > seen[item["id"]]["score"]:
                seen[item["id"]] = item
        sparse = sorted(seen.values(), key=lambda x: x["score"], reverse=True)[:top_k * 2]
    else:
        sparse = lexical_search(query, top_k=top_k * 2)

    hybrid = (
        rerank_rrf([dense, sparse], top_k=top_k)
        if use_reranking else dense[:top_k]
    )


    best_dense_score = dense[0]["score"] if dense else 0.0
    if best_dense_score < score_threshold:
        try:
            fallback = pageindex_search(query, top_k=top_k)
            if fallback:
                return fallback
        except Exception:
            pass
    return hybrid[:top_k]



if __name__ == "__main__":
    for result in retrieve("test query", top_k=3):
        print(result)
