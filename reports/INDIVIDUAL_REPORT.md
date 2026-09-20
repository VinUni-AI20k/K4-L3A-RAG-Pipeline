# Báo cáo đóng góp cá nhân

## Thông tin

- Họ và tên: Trần Long Khánh
- Mã học viên: 2A202602538
- Nhóm: ActionPlan
- Repository/branch: `khanh`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 4 — Chunking và indexing | Đọc toàn bộ Markdown đã chuẩn hóa; chia văn bản bằng `RecursiveCharacterTextSplitter` với `chunk_size=500`, `chunk_overlap=50`; tạo ID chunk ổn định và giữ metadata nguồn; lưu 969 chunks thành corpus JSON cho BM25. | `src/task4_chunking_indexing.py`; `data/indexes/bm25_corpus.json`; commit `2ad5e59` | Done |
| Task 5 — Search interface | Hoàn thiện `semantic_search()` theo contract dense search với cosine similarity; hỗ trợ chạy file trực tiếp; khi cấu hình hiện tại là BM25, CLI chuyển sang lexical search để không tải embedding model hoặc truy vấn Chroma chưa được index. | `src/task5_semantic_search.py`; commit `2ad5e59` | Done, dense path chưa dùng trong cấu hình BM25 |
| Task 6 — BM25 lexical search | Xây dựng tokenizer Unicode cho tiếng Việt, nạp corpus Task 4, tạo `BM25Okapi`, lọc chunk có token khớp, sắp xếp giảm dần theo score và trả đúng schema `SearchResult`. | `src/task6_lexical_search.py`; commit `2ad5e59` | Done |

## Quyết định kỹ thuật quan trọng

1. **Dùng BM25 làm cơ chế retrieval đang hoạt động thay vì khai báo `bm25` như một SentenceTransformer model.**

   **Lý do/evidence:** `sentence-transformers/bm25` không phải model embedding hợp lệ và gây lỗi HTTP 401 khi Hugging Face tìm `modules.json`. Sau thay đổi, Task 4 tạo 969 chunks cục bộ mà không cần tải BGE-M3; truy vấn thử “học phí tuyển sinh” trả đúng các đoạn liên quan đến học bổng và hỗ trợ học phí.

   **Trade-off:** Khởi động nhanh, không phụ thuộc model lớn hoặc mạng; đổi lại BM25 chủ yếu khớp từ khóa và không hiểu tương đồng ngữ nghĩa tốt như dense embedding.

2. **Dùng ID ổn định theo mẫu `<document-id>::chunk-<index>` và giữ nguyên metadata qua các bước chunk/search.**

   **Lý do/evidence:** Cách này đáp ứng module contract, giúp truy vết kết quả về file nguồn và tránh sinh ID ngẫu nhiên khi chạy lại pipeline. BM25 trả đủ `id`, `content`, `score`, `metadata` và `retrieval_method`.

   **Trade-off:** Khi thay đổi kích thước hoặc chiến lược chunking, chỉ số chunk và corpus phải được tạo lại.

## Kiểm thử và kết quả

- Lệnh kiểm thử: `python -m pytest tests/test_contracts.py::test_chunk_documents_preserves_identity_and_metadata tests/test_contracts.py::test_semantic_search_uses_shared_embedding_and_contract tests/test_contracts.py::test_lexical_search_returns_bm25_contract -q`.
- Kết quả kiểm tra chung ba contract của Task 4–6: `3 passed`.
- Chạy `python .\src\task4_chunking_indexing.py` tạo thành công 969 chunks trong `data/indexes/bm25_corpus.json` mà không gọi Hugging Face.
- Query kiểm tra `học phí tuyển sinh`, `top_k=3` trả các chunk từ `article_02.md` và `article_05.md`, với BM25 score cao nhất khoảng `9.3158`.
- Lỗi đã xử lý: lỗi 401 do dùng sai tên model `sentence-transformers/bm25`; lỗi relative import khi chạy trực tiếp Task 5/6; trường hợp IDF bằng 0 trên corpus rất nhỏ được xử lý bằng cách lọc token overlap thay vì loại toàn bộ kết quả có score 0.

## Điều còn hạn chế

- Cấu hình hiện tại ưu tiên BM25 nên chưa có dense vector index thực tế trong ChromaDB; `semantic_search()` chỉ hoạt động theo dense path khi chọn một embedding model hợp lệ và chạy lại Task 4 để index vectors.
- Nếu có thêm thời gian, tôi sẽ bổ sung một embedding model tiếng Việt nhẹ hơn BGE-M3, đánh giá A/B dense so với BM25 trên golden dataset, sau đó kết hợp hai danh sách bằng RRF.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Trần Long Khánh
