# Individual contribution report

## Thông tin

- Họ và tên: Trần Phạm Thái Vũ
- Mã học viên: 2A202602695
- Nhóm: Nhóm Tuyển sinh đại học 2026 (`K4-L3A-RAG-Pipeline-LacRang`)
- Repository: `https://github.com/yohan-vinai/K4-L3A-RAG-Pipeline-LacRang`
- Branch: `contrib/elysszxje`

---

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| **Task 4: Chunking, Embedding & ChromaDB Indexing** | Đọc 8 văn bản tuyển sinh chuẩn hóa (3 pháp lý, 5 bài viết). Xây dựng `chunk_documents()` với separator tiếng Việt chuyên dụng (`Điều`, `Khoản`, `\n\n`) tạo 627 chunks bảo toàn bảng biểu. Tích hợp OpenAI `text-embedding-3-small` (1536 dim, batch 128 chunks), thiết lập persistent ChromaDB với cosine distance metric và cơ chế làm sạch metadata. | `src/task4_chunking_indexing.py`<br>Commit: `87bc194`<br>Branch: `contrib/elysszxje` | Done |
| **Task 5: Semantic Search (Dense Retrieval)** | Tái sử dụng `embed_texts()` và `get_collection()` từ Task 4, vector hóa câu hỏi truy vấn của thí sinh, truy vấn ChromaDB, chuẩn hóa khoảng cách cosine sang similarity score $\max(0.0, 1.0 - \text{distance})$, sắp xếp giảm dần và trả về đúng chuẩn `SearchResult`. | `src/task5_semantic_search.py`<br>Commit: `52ad7e2`<br>Branch: `contrib/elysszxje` | Done |
| **Task 6: Lexical Search (BM25 Sparse Retrieval)** | Xây dựng lớp `RobustBM25Okapi` với công thức IDF làm mịn $\ln(1 + \frac{N - n + 0.5}{n + 0.5})$ giải quyết lỗi Zero IDF của thư viện `rank_bm25`. Lazy loading và caching index trên 627 chunks, lọc điểm $> 0$, trả về `SearchResult` với `retrieval_method="bm25"`. | `src/task6_lexical_search.py`<br>Commit: `c0aaa5a`<br>Branch: `contrib/elysszxje` | Done |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định 1: Sử dụng mô hình OpenAI `text-embedding-3-small` kết hợp batch processing (batch size 128) và ChromaDB Persistent Client.**  
   - **Lý do/evidence:** Bộ dữ liệu tuyển sinh có 627 chunks. Mô hình `text-embedding-3-small` (1536 chiều) có khả năng hiểu ngữ nghĩa tiếng Việt vượt trội, tốc độ embed toàn bộ corpus chỉ mất dưới 10 giây qua batch API, đồng thời tránh việc phải tải mô hình cục bộ nặng 2.2GB (như BGE-M3) gây tiêu tốn tài nguyên RAM/VRAM máy cá nhân.  
   - **Trade-off:** Cần kết nối mạng và tiêu tốn một lượng nhỏ chi phí OpenAI API thay vì chạy hoàn toàn offline.

2. **Quyết định 2: Tùy biến công thức IDF trong `RobustBM25Okapi` thành $\text{IDF} = \ln\left(1 + \frac{N - n + 0.5}{n + 0.5}\right)$.**  
   - **Lý do/evidence:** Thư viện `rank_bm25` mặc định sử dụng công thức $\ln\left(\frac{N - n + 0.5}{n + 0.5}\right)$, dẫn đến việc khi một từ khóa xuất hiện ở 50% số văn bản (hoặc trong các unit test nhỏ có 2 documents), giá trị bên trong hàm log bằng 1 và IDF bị bằng 0. Điều này làm điểm BM25 bị triệt tiêu về 0, gây rớt contract test. Công thức làm mịn (tương tự như Lucene/Elasticsearch) đảm bảo điểm IDF luôn dương và phân hạng chính xác các từ khóa đặc trưng như mã ngành, tên khối thi.  
   - **Trade-off:** Phải kế thừa và tính toán lại bảng IDF khi khởi tạo index, nhưng chi phí phụ trội này không đáng kể trên tập corpus thực tế.

---

## Kiểm thử và kết quả

- **Test suite tự động:** Chạy và pass 100% các contract tests liên quan:
  ```bash
  pytest tests/test_contracts.py -k "chunk_documents or semantic_search or lexical_search or public_function_signatures or validator"
  ```
  *(Kết quả: 10 passed, 0 failed).*
- **Thử nghiệm truy vấn thực tế:**
  - *Task 5 (Dense Search)*: Query `"quy chế tuyển sinh đại học"` trả về top 1 chunk thuộc Quyết định 955/QĐ-ĐHQGHN với similarity score `0.6552`.
  - *Task 6 (BM25 Search)*: Query `"học phí Đại học Quốc gia"` trả về top 1 chunk thuộc Quyết định 955 với điểm BM25 `11.8836`.
- **Lỗi đã phát hiện và cách xử lý:**
  - *Lỗi 1*: Metadata chứa giá trị `None` (ở trường `url`) khiến thư viện ChromaDB (Rust binding) báo lỗi `TypeError: Cannot convert Python object to MetadataValue`. Đã viết hàm `_sanitize_metadata_for_chroma` chuyển `None` thành `""` trước khi upsert vào Chroma và khôi phục lại khi truy vấn.
  - *Lỗi 2*: Trên hệ điều hành Windows, lệnh `print()` nội dung tiếng Việt ở hàm `__main__` bị lỗi mã hóa `UnicodeEncodeError: 'charmap' codec can't encode`. Đã bổ sung cấu hình `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")`.

---

## Điều còn hạn chế

- **Một hạn chế cụ thể:** Việc tiền xử lý tách từ cho BM25 hiện tại mới dùng phương pháp tách từ theo khoảng trắng (`split()`), chưa tích hợp bộ tách từ ghép tiếng Việt chuyên biệt.
- **Nếu có thêm thời gian:** Tôi sẽ tích hợp thư viện tách từ tiếng Việt (như `pyvi` hoặc `underthesea`) để các cụm từ ghép chuyên môn trong tuyển sinh (ví dụ: `xét_tuyển`, `học_bổng`, `điểm_chuẩn`, `chỉ_tiêu`) được gom thành một token duy nhất, nâng cao hơn nữa độ chính xác của BM25.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: **Trần Phạm Thái Vũ**

