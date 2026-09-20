# Individual contribution report

## Thông tin

- Họ và tên: Đoàn Quang Minh
- Mã học viên: 2A202602711
- Lớp: K4-L3A
- Nhóm: Phronesis
- Repository/branch: https://github.com/nthanhwork/K4-L3A-RAG-Pipeline / branch: main

---

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| **Task 1 — Thu thập văn bản pháp luật** | Thu thập 3 tài liệu pháp quy gốc dạng PDF về cơ chế tài chính và tái cơ cấu doanh nghiệp: Nghị định 359/2026/NĐ-CP (VAMC), Nghị định 358/2026/NĐ-CP (DATC), và Nghị định 357/2026/NĐ-CP (Quản lý nguồn thu cổ phần hóa). | `data/landing/legal/` | Done |
| **Task 2 — Crawl bài báo & tin tức** | Thu thập và xử lý 5 bài báo chuyên ngành tài chính - ngân hàng từ các nguồn báo chính thống (Nhân Dân, Báo Đấu Thầu, BNews TTXVN, VOV) kèm đầy đủ metadata (`url`, `title`, `date_crawled`, `content_markdown`). | `src/task2_crawl_news.py`, `data/landing/news/` | Done |
| **Task 3 — Chuẩn hóa dữ liệu sang Markdown** | Xây dựng pipeline trích xuất văn bản từ PDF và HTML sang định dạng Markdown chuẩn hóa, phân loại rõ ràng thành 2 thư mục `standardized/legal/` và `standardized/news/`. | `src/task3_convert_markdown.py`, `data/standardized/` | Done |
| **Task 4 — Chunking & Indexing vào ChromaDB** | Cài đặt hàm `chunk_documents` (RecursiveCharacterTextSplitter với `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`), embedding qua OpenAI `text-embedding-3-small` (1536 dims) và nạp 44 chunks vào vector collection `rag_documents`. | `src/task4_chunking_indexing.py` | Done |
| **Acceptance Test (Dữ liệu)** | Đảm bảo toàn bộ tiêu chí chấp nhận dữ liệu (Corpus has required legal docs, news with metadata, standardized output) pass 100%. | `tests/test_acceptance.py` | Done |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định: Lựa chọn kích thước Chunking vừa phải (CHUNK_SIZE = 500 ký tự, CHUNK_OVERLAP = 50 ký tự) cho văn bản quy phạm pháp luật.**  
   - **Lý do/evidence:** Văn bản pháp quy Việt Nam thường có cấu trúc chặt chẽ theo từng Khoản, Điểm với độ dài trung bình từ 300 đến 600 ký tự. Kích thước 500 ký tự giúp mỗi chunk gói gọn được ít nhất một quy định cụ thể (như mức vốn điều lệ, thẩm quyền quản lý hoặc một nhóm ngành nghề) mà không bị pha loãng ngữ nghĩa khi chuyển thành vector embedding. Overlap 50 ký tự đảm bảo ranh giới giữa các câu quy định không bị cắt rời ngữ cảnh.  
   - **Trade-off:** Đối với các điều khoản dài có nhiều điểm liệt kê, chunk 500 ký tự có thể bị chia thành 2 chunk liên tiếp; tuy nhiên việc này được bù đắp tốt nhờ kỹ thuật Hybrid Search (BM25 + Dense RRF) ở khâu retrieval.

2. **Quyết định: Chuẩn hóa siêu dữ liệu (Metadata) đồng bộ xuyên suốt từ Landing sang Vectorstore.**  
   - **Lý do/evidence:** Mỗi chunk sau khi tách đều bắt buộc phải lưu giữ metadata gốc: `source` (tên tệp), `title` (tiêu đề văn bản), `doc_type` (`legal` hoặc `news`), `url` và `chunk_index`. Việc này giúp tầng Generation và Streamlit UI có thể truy ngược chính xác nguồn gốc, trích dẫn số trang/văn bản và hiển thị liên kết tham khảo nguyên bản cho người dùng.  
   - **Trade-off:** Tăng dung lượng lưu trữ metadata trong ChromaDB SQLite, nhưng đảm bảo tính nhất quán tuyệt đối của hợp đồng dữ liệu (`Document` & `SearchResult` schema).

---

## Kiểm thử và kết quả

- **Các bài kiểm thử đã thực hiện:**
  - `pytest tests/test_acceptance.py -k "test_corpus or test_standardized"`: Đạt 3/3 passed (đủ 3 văn bản pháp luật hợp lệ > 1KB, đủ 5 JSON tin tức có đủ 4 trường metadata, đủ 8 tệp markdown chuẩn hóa > 200 ký tự).
  - `pytest tests/test_contracts.py -k "test_chunk_documents"`: Xác nhận các chunk sinh ra có ID duy nhất, bảo toàn metadata nguồn và không vượt quá kích thước cho phép.
  - Chạy `python -m src.task4_chunking_indexing`: Nạp thành công 44 chunks vào ChromaDB không bị trùng lặp.
- **Lỗi đã phát hiện và cách xử lý:**
  - Khi tách chunk từ PDF ban đầu, một số bảng biểu bị vỡ format; đã tinh chỉnh tiền xử lý văn bản trong Task 3 để loại bỏ khoảng trắng thừa và giữ lại cấu trúc phân cấp danh sách.

---

## Điều còn hạn chế

- **Hạn chế:** Bộ dữ liệu pháp lý hiện tại tập trung vào 3 nghị định mới ban hành tháng 9/2026; chưa bao quát hết các thông tư hướng dẫn chi tiết của Bộ Tài chính và Ngân hàng Nhà nước.
- **Nếu có thêm thời gian:** Tôi sẽ xây dựng parser nhận diện tự động cấu trúc pháp lý (Điều/Khoản/Điểm) bằng `MarkdownHeaderTextSplitter` để mỗi chunk luôn là một Điều luật trọn vẹn.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Đoàn Quang Minh
