# Individual contribution report

## Thông tin

- Họ và tên: Vũ Minh Hoàng
- Mã học viên: 2A202602371
- Nhóm: RAG Pipeline — nhóm 4 thành viên
- Repository/branch: `name/vuminhhoang_2A202602371`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 4 — Chunking, embedding & indexing | Đọc Markdown đã chuẩn hóa, parse front matter, tạo chunk ID ổn định kèm metadata, embed bằng SentenceTransformer và upsert idempotent vào ChromaDB theo cosine distance. | `src/task4_chunking_indexing.py`, commit `8e72251` | Done |
| Task 5 — Semantic search | Dùng chung `embed_texts()` của Task 4 để embed query, truy vấn ChromaDB, đổi cosine distance thành similarity và trả dense result đúng contract. | `src/task5_semantic_search.py`, commit `8e72251` | Done |
| Task 6 — Lexical search | Xây dựng BM25 trên chính corpus chunk, token hóa Unicode và trả các kết quả có score dương theo thứ tự giảm dần; có fallback BM25 tối giản khi môi trường thiếu package. | `src/task6_lexical_search.py`, commit `8e72251` | Done |
| Task 7 — RRF reranking | Hợp nhất danh sách dense/BM25 bằng Reciprocal Rank Fusion, khử trùng ID trong từng ranking và gắn `retrieval_method="hybrid"`. | `src/task7_reranking.py`, commit `8e72251` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng ID dạng `<relative-path>::chunk-<index>` và giữ toàn bộ metadata nguồn trên mỗi chunk.
   **Lý do/evidence:** ID ổn định giúp ChromaDB `upsert` an toàn khi chạy lại; các trường `source`, `title`, `doc_type`, `url` và `chunk_index` đáp ứng contract chung, phục vụ citation ở Task 10.
   **Trade-off:** Khi nội dung nguồn thay đổi mạnh, chỉ số chunk có thể thay đổi; cần chạy index lại để đồng bộ các chunk cũ.

2. **Quyết định:** Không cộng trực tiếp dense cosine similarity với BM25 score, mà dùng RRF với công thức `sum(1 / (k + rank))`.
   **Lý do/evidence:** Hai thang điểm khác nhau; RRF chỉ dùng thứ hạng nên kết hợp được exact-match của BM25 và ngữ nghĩa của dense search mà không cần chuẩn hóa score.
   **Trade-off:** RRF score không thể dùng làm ngưỡng confidence; Task 9 phải so fallback bằng dense cosine score gốc.

## Kiểm thử và kết quả

- Đã chạy smoke test cục bộ: `load_documents()` đọc 8 Markdown chuẩn hóa và `chunk_documents()` tạo 475 chunk không rỗng, ID duy nhất, có `chunk_index`.
- Đã giả lập Chroma collection để kiểm tra semantic search dùng embedding chung, sắp xếp theo similarity và trả đúng cấu trúc dense result.
- Đã kiểm tra BM25 với truy vấn `học bổng`, RRF với hai ranking có ID trùng, cùng `python -m py_compile` cho bốn module và `git diff --check`.
- Kết quả: các smoke check đạt; không chạy được `python -m pytest tests/test_contracts.py -q` vì môi trường hiện tại chưa cài module `pytest`.
- Lỗi đã phát hiện: môi trường thiếu `rank-bm25`; đã bổ sung BM25 fallback tương thích để lexical search vẫn hoạt động trong môi trường tối giản, trong khi vẫn ưu tiên package chính thức khi có sẵn.

## Điều còn hạn chế

- Lần chạy indexing đầy đủ cần cài `sentence-transformers`, `chromadb` và tải model `BAAI/bge-m3`; chưa thực hiện được trong môi trường hiện tại vì các dependency này chưa có.
- Nếu có thêm thời gian, tôi sẽ benchmark `CHUNK_SIZE`, `CHUNK_OVERLAP` và `k` của RRF trên golden dataset để chọn thông số dựa trên retrieval metrics.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Vũ Minh Hoàng
