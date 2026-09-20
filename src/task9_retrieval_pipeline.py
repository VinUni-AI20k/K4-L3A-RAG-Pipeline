"""
Task 9 — Retrieval pipeline hoàn chỉnh.

Luồng xử lý:
    1. Chạy semantic_search và lexical_search.
    2. Fuse hai danh sách bằng RRF đúng một lần.
    3. Lấy best cosine score gốc từ dense results.
    4. Nếu score dưới threshold, thử PageIndex fallback.
    5. Nếu fallback lỗi hoặc rỗng, trả hybrid results thay vì crash.

Threshold so với cosine score gốc của dense, KHÔNG so với RRF score: RRF score
chỉ là tổng nghịch đảo thứ hạng (cỡ 0.01-0.03) nên không có ý nghĩa về độ
tương đồng.
"""

import os

from dotenv import load_dotenv

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import pageindex_search


load_dotenv()

# Hiệu chỉnh trên corpus của nhóm với paraphrase-multilingual-MiniLM-L12-v2,
# đo bằng 8 query in-domain và 8 query out-of-domain:
#   in-domain      : 0.360 - 0.791
#   out-of-domain  : 0.135 - 0.336
# 0.35 là điểm duy nhất tách được hai vùng. Biên chỉ rộng 0.024 (0.360 so với
# 0.336), nên khi mở rộng corpus phải đo lại bằng nhiều query OOD hơn trước
# khi tin vào con số này. Đổi embedding model cũng phải đo lại từ đầu.
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD") or 0.35)
DEFAULT_TOP_K = 5


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Trả về hybrid hoặc pageindex SearchResult."""
    try:
        dense = semantic_search(query, top_k=top_k * 2)
    except Exception as error:
        print(f"Semantic search lỗi: {error}")
        dense = []

    try:
        sparse = lexical_search(query, top_k=top_k * 2)
    except Exception as error:
        print(f"Lexical search lỗi: {error}")
        sparse = []

    if use_reranking:
        hybrid = rerank_rrf([dense, sparse], top_k=top_k)
    else:
        hybrid = dense[:top_k]

    best_dense_score = dense[0]["score"] if dense else 0.0
    if best_dense_score < score_threshold:
        try:
            fallback = pageindex_search(query, top_k=top_k)
            if fallback:
                return fallback
        except Exception as error:
            print(f"PageIndex fallback lỗi: {error}")

    return hybrid[:top_k]


if __name__ == "__main__":
    queries = [
        "Shopee hỗ trợ những phương thức thanh toán nào?",
        "Làm sao để yêu cầu trả hàng hoàn tiền?",
        "xyzabc123nonsense",
    ]
    for query in queries:
        print(f"\nQuery: {query}")
        for result in retrieve(query, top_k=3):
            print(
                f"  [{result['score']:.4f}] ({result['retrieval_method']}) "
                f"{result['id']} — {result['content'][:70]}..."
            )
