# Individual Contribution Report

---

## Thông tin

- **Họ và tên:** Đinh Xuân Quyền
- **Mã học viên:** 2A202602358
- **Nhóm:** K4-L3A — RAG Pipeline PTIT
- **Repository/branch:** K4-L3A-RAG-Pipeline-MegaLive / main

---

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
| ------------------ | ----------------------- | -------------- | ---------- |
| Chunking (Task 4) | Code hàm tách đoạn văn bản tài liệu dài thành các khối nhỏ (chunks) theo ngắt dòng tự nhiên | `src/task4_chunking_indexing.py` | Hoàn thành |
| CSDL Vector ChromaDB (Task 4)| Code phần nhúng embedding và đẩy data (upsert) vào cơ sở dữ liệu vector Chroma | `src/task4_chunking_indexing.py` | Hoàn thành |
| Tìm kiếm ngữ nghĩa (Task 5) | Viết hàm tìm kiếm theo độ tương đồng ngữ nghĩa (cosine similarity) lấy chunk từ ChromaDB | `src/task5_semantic_search.py` | Hoàn thành |
| Tìm kiếm từ khóa BM25 (Task 6) | Dùng thư viện `rank_bm25` để viết module tìm kiếm chính xác theo từ khóa truyền thống | `src/task6_lexical_search.py` | Hoàn thành |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng thuật toán `HashingVectorizer` chạy giả embedding thay vì model chuẩn.
   **Lý do/evidence:** Máy tính trên phòng lab và laptop cá nhân nhóm tôi hơi yếu, nếu chạy mấy model embedding như `bge-m3` hay tải model lớn về sẽ rất nặng, cài đặt môi trường GPU cũng phức tạp. Tôi quyết định dùng một hàm băm vector nhẹ của sklearn để làm giả embedding, giúp code chạy thông suốt toàn bộ luồng xử lý trước.
   **Trade-off:** Chất lượng tìm kiếm ngữ nghĩa cực kỳ kém (test đo ra Context Precision chỉ đạt 0.50), model không hiểu được nghĩa của từ đồng nghĩa mà chỉ so khớp chuỗi băm.

2. **Quyết định:** Cắt văn bản (chunk) theo dấu ngắt dòng thay vì giới hạn số ký tự cố định.
   **Lý do/evidence:** Xem qua file thông báo tuyển sinh và học phí, toàn là các mục lục và gạch đầu dòng ngắn. Nếu cắt theo đúng 500 ký tự thì bảng biểu thường xuyên bị đứt làm đôi, bot LLM đọc không hiểu. Việc cắt theo đoạn (paragraph) giữ được logic mạch văn.
   **Trade-off:** Kích thước các chunk tạo ra bị to nhỏ rất lộn xộn, không đồng đều, có chunk quá ngắn.

---

## Kiểm thử và kết quả

- **Test đã dùng:** Code hàm in ra terminal để check nhanh kết quả: `semantic_search("học phí PTIT 2026")`
- **Kết quả:** Code ChromaDB đã chạy thành công, lưu file vào ổ cứng. So sánh bằng mắt thì BM25 bắt chính xác từ "học phí" trả về văn bản đúng ngay top 1, còn Dense (dùng Hashing) trả kết quả hơi lệch. Nhờ chạy test này mới biết cần phải có thuật toán hybrid kết hợp cả hai.
- **Lỗi đã phát hiện và cách xử lý:** Lúc ấn chạy code tạo index 2 lần liên tiếp thì ChromaDB cứ thế cộng dồn làm nhân đôi dữ liệu. Tôi phải sửa code thêm đoạn `collection.delete()` hoặc bắt check ID trùng để nó xóa/đè bản ghi cũ trước khi upsert cái mới.

---

## Điều còn hạn chế

- Việc dùng `HashingVectorizer` là điểm yếu lớn nhất của dự án này, làm AI ngốc đi hẳn khi tìm kiếm tài liệu.
- Nếu có thêm thời gian, điều đầu tiên tôi làm là đăng ký khóa API của OpenAI hoặc dùng `text-embedding-3-small` để thay vào, chất lượng tìm kiếm sẽ đột phá ngay lập tức.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- **Ngày:** 2026-09-20
- **Tên thành viên:** Đinh Xuân Quyền
