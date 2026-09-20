# Individual contribution report

## Thông tin

- Họ và tên: Trịnh Hoàng Tùng
- Mã học viên: 2A202602937
- Nhóm: phoboi
- Repository/branch: `K4-L3A-RAG-Pipeline-phoboi` / `htungf`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 1 | Thu thập 3 văn bản chính sách và kiểm tra định dạng, kích thước | `data/landing/legal/` | Done |
| Task 2 | Thu thập 5 bài du lịch, crawl JSON và loại menu/footer | `src/task2_crawl_news.py`, `data/landing/news/` | Done |
| Task 3 | Chuẩn hóa legal/news sang Markdown, giữ metadata nguồn | `src/task3_convert_markdown.py`, `data/standardized/` | Done |

## Quyết định kỹ thuật quan trọng

1. Giữ `raw_content_markdown` để đối chiếu và dùng `content_markdown` đã làm sạch cho RAG.
2. Dùng `data/landing/legal/sources.json` để quản lý tiêu đề và URL nguồn legal.

## Kiểm thử và kết quả

- Chạy ba acceptance test dành cho Task 1–3.
- Kết quả: `3 passed`.
- Đã xử lý menu/footer của website và các file Word sai định dạng.

## Điều còn hạn chế

- Bộ legal hiện thiên về văn hóa, di sản hơn hướng dẫn du lịch tổng quát.
- Nếu có thêm thời gian, tôi sẽ bổ sung văn bản trực tiếp về hoạt động du lịch.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Trịnh Hoàng Tùng
