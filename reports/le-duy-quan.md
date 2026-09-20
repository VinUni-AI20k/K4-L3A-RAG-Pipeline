# Individual contribution report

## Thông tin

- Họ và tên: Lê Duy Quân
- Mã học viên: 2A202602731
- Nhóm: RAG Pipeline — nhóm 4 thành viên
- Repository/branch: `name/leduyquan_2A202602731`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 1 — Legal corpus | Chọn corpus chính sách sinh viên UEH, cấu hình ba URL PDF chính thức và tải file gốc có kiểm tra kích thước/response. | `src/task1_collect_legal_docs.py`, `data/landing/legal/` | Done |
| Task 2 — News corpus | Crawl năm trang thông báo UEH; lưu JSON có đủ `url`, `title`, `date_crawled`, `content_markdown`; lỗi một URL không làm dừng toàn bộ lượt crawl. | `src/task2_crawl_news.py`, `data/landing/news/` | Done |
| Task 3 — Standardization | Chuyển PDF/DOCX bằng MarkItDown và JSON bài viết thành Markdown; thêm front matter để giữ title, source, doc type và URL. | `src/task3_convert_markdown.py`, `data/standardized/` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng tài liệu và bài viết từ các website UEH về chính sách sinh viên.
   **Lý do/evidence:** Corpus nhất quán về học phí, học bổng, đào tạo, ký túc xá và bảo hiểm; thuận tiện tạo câu hỏi retrieval có nguồn đối chiếu được.
   **Trade-off:** Corpus tập trung vào một trường nên phạm vi trả lời hẹp hơn dữ liệu nhiều nguồn.

2. **Quyết định:** Chuẩn hóa dữ liệu vào Markdown có front matter.
   **Lý do/evidence:** `source`, `title`, `doc_type` và `url` được giữ lại để Task 4 tạo document metadata và Task 10 hiển thị citation.
   **Trade-off:** Cần kiểm tra nội dung crawl và chuyển đổi trước khi indexing để tránh văn bản quá ngắn hoặc metadata thiếu.

## Kiểm thử và kết quả

- Đã chạy bằng môi trường `lab-vin-env`:

  ```bash
  python -m src.task1_collect_legal_docs
  python -m src.task2_crawl_news
  python -m src.task3_convert_markdown
  python -m pytest tests/test_acceptance.py -q -k 'corpus_has_required_legal_documents or corpus_has_required_news_with_metadata or standardized_output_covers_both_source_types'
  ```

- Kết quả: `3 passed, 2 deselected`.
- Corpus đầu ra: 3 PDF (269–714 KB), 5 JSON bài viết và 8 Markdown chuẩn hóa; toàn bộ Markdown có nội dung vượt ngưỡng acceptance test.
- Lỗi đã phát hiện: môi trường `lab-vin-env` thiếu MarkItDown; đã cài dependency theo `pyproject.toml` trước khi chạy Task 3.

## Điều còn hạn chế

- Parser HTML hiện trích xuất các thẻ nội dung phổ biến; một số bố cục web động có thể giữ lại nội dung điều hướng thừa.
- Nếu có thêm thời gian, tôi sẽ bổ sung kiểm tra chất lượng nội dung theo từng URL và danh sách nguồn/version của từng văn bản pháp lý.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Lê Duy Quân
