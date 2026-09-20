# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Mai Hoàng Thiện
- Mã học viên: 2A202602912
- Repository/branch: hoanganhb680-arch/K4-L3A-RAG-Pipeline / branch `thiennmh`

## Phần việc đã thực hiện

| Module/deliverable           | Việc tôi trực tiếp làm                                                                                                  | File/commit/PR                                   | Trạng thái |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ | ---------- |
| Task 5 – Semantic Search     | Implement `semantic_search()` với cosine similarity qua ChromaDB; trả về `SearchResult` đúng contract                   | `src/task5_semantic_search.py`                   | Done       |
| Task 6 – Lexical Search      | Implement `lexical_search()` với BM25Okapi; tokenize tiếng Việt bằng `underthesea`; trả đúng `SearchResult`             | `src/task6_lexical_search.py`                    | Done       |
| Task 7 – RRF Reranking       | Implement `rerank_rrf()` fusing multiple ranked lists; tính RRF score = Σ 1/(k+rank)                                    | `src/task7_reranking.py`                         | Done       |
| A/B Evaluation               | Xây dựng script so sánh Config A (Dense-only) vs Config B (Hybrid+RRF) với Ragas; golden dataset 15 câu                 | `evaluate_ragas.py`, `group_project/evaluation/` | Done       |
| Streamlit app                | Tích hợp pipeline vào giao diện chat; hiển thị sources và citation                                                      | `app.py`                                         | Done       |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng RRF (Reciprocal Rank Fusion) thay vì weighted sum để fuse dense + BM25
**Lý do/evidence:** RRF không cần chuẩn hóa score vì hai hệ thống (cosine similarity vs BM25 score) có thang đo hoàn toàn khác nhau. Kết quả Config B (Hybrid+RRF) cho thấy context recall cao hơn Config A.
**Trade-off:** RRF bỏ qua magnitude của score, chỉ dùng rank — phù hợp khi không có validation set để tune weights.
2. **Quyết định:** Giữ threshold dựa trên cosine score từ dense search (không dùng RRF score) để quyết định fallback
**Lý do/evidence:** RRF score và cosine score không cùng thang đo; so sánh threshold với RRF score cho kết quả sai. Dense cosine score đại diện cho semantic relevance tốt hơn.
**Trade-off:** Nếu dense search kém nhưng BM25 tốt (keyword match), system vẫn có thể fallback sai. Cần thêm validation để tìm threshold tối ưu.

## Kiểm thử và kết quả

- **Contract tests:** `pytest tests/test_contracts.py` — 14/15 pass (test `lexical_search_returns_bm25_contract` fail do mock corpus không đủ BM25 signal)
- **Acceptance tests:** `pytest tests/test_acceptance.py` — pass sau khi bổ sung corpus tài liệu du lịch/pháp lý Việt Nam
- **A/B Evaluation:** Chạy Ragas với 15 golden cases, so sánh Dense-only vs Hybrid+RRF trên 4 metrics: Faithfulness, Answer Relevancy, Context Recall, Context Precision
- **Lỗi phát hiện:** `models/embedding-001` deprecated → fix sang `models/gemini-embedding-001`; `generate_with_citation()` thiếu param `use_reranking` → thêm vào để hỗ trợ A/B test

## Điều còn hạn chế

- **Hạn chế:** BM25 tokenize bằng `underthesea` chưa tối ưu cho thuật ngữ pháp lý/du lịch — một số câu hỏi keyword-based trả về chunk không liên quan
- **Nếu có thêm thời gian:** Thêm cross-encoder reranker (ví dụ `cross-encoder/ms-marco-MiniLM-L-6-v2`) sau RRF để refine top-k trước khi đưa vào LLM; tinh chỉnh SCORE\_THRESHOLD bằng precision-recall curve trên validation set

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Mai Hoàng Thiện
