# Báo cáo đóng góp cá nhân

## Thông tin

- Họ và tên: Nguyễn Quang Huy
- Mã học viên: 2A202602820
- Nhóm: 22
- Repository: `taitottinhday/K4-L3A-RAG-Pipeline`
- Nhánh: `feature/retrieval-fusion`
- Commit đối chiếu: `ab32141` — `done task 5 6 7 8 9`

## Phần việc đã thực hiện

| Module/deliverable | Việc trực tiếp thực hiện | File/commit | Trạng thái |
| --- | --- | --- | --- |
| Task 5 — Dense retrieval | Embed query bằng cùng hàm với corpus, truy vấn Chroma và đổi cosine distance thành similarity | `src/task5_semantic_search.py`, `ab32141` | Done |
| Task 6 — BM25 | Tạo BM25 trên cùng corpus chunks, chuẩn hóa kết quả theo `SearchResult` | `src/task6_lexical_search.py`, `ab32141` | Done |
| Task 7 — RRF | Gộp dense/BM25 theo ID bằng `1/(k+rank)`, rank từ 1, không mutate input | `src/task7_reranking.py`, `ab32141` | Done |
| Task 8 — PageIndex | Upload/cache document ID, parse kết quả fallback và trả schema thống nhất | `src/task8_pageindex_vectorless.py`, `ab32141` | Done |
| Task 9 — Retrieval pipeline | Nối dense + BM25 + một lần RRF; fallback bằng cosine dense gốc và xử lý provider lỗi | `src/task9_retrieval_pipeline.py`, `ab32141` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng Reciprocal Rank Fusion với `k=60` thay vì cộng trực tiếp dense score và BM25 score.  
   **Lý do/evidence:** Hai score thuộc thang đo khác nhau; RRF chỉ dùng thứ hạng và ưu tiên chunk xuất hiện cao ở cả hai danh sách.  
   **Trade-off:** RRF đơn giản, tái lập và không gọi API nhưng không phải cross-encoder reranker học theo ngữ nghĩa.

2. **Quyết định:** Fallback dùng `dense[0].score` với `SCORE_THRESHOLD=0.30`; PageIndex lỗi/rỗng thì trả hybrid.  
   **Lý do/evidence:** Điểm RRF rất nhỏ và không biểu diễn cosine confidence. Query trong domain đạt khoảng `0.345`, query ngoài domain khoảng `0.155`.  
   **Trade-off:** Threshold phụ thuộc corpus; cần hiệu chỉnh lại khi đổi embedding hoặc dữ liệu.

## Kiểm thử và kết quả

- Dense và BM25 trả kết quả cùng schema, không trùng ID và được sắp xếp giảm dần.
- RRF chỉ được gọi một lần trong `retrieve()`; fallback không làm UI crash khi provider không khả dụng.
- `pytest tests/test_contracts.py -q`: **15 passed**.
- `pytest tests/test_acceptance.py -q`: **5 passed**.
- `pytest -q`: **20 passed** trên `main` sau khi merge ba phần.
- Evaluation: dense-only average `0.870`; hybrid + RRF `0.893`, tăng `0.023`.

## Điều còn hạn chế

- `SCORE_THRESHOLD=0.30` mới được hiệu chỉnh trên số lượng query nhỏ.
- PageIndex là dịch vụ tùy chọn và chưa được dùng trong A/B retrieval cơ bản.
- Nếu có thêm thời gian, cải tiến đầu tiên là đo precision/recall của threshold trên tập in-domain/out-of-domain lớn hơn và so sánh thêm cross-encoder reranker.

## Xác nhận đóng góp

Nội dung trên được đối chiếu với commit `ab32141`.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Quang Huy
