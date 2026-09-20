# Individual contribution report

## Thông tin

- Họ và tên: Trần Quốc Bảo Long
- Mã học viên: 2A202602696
- Nhóm: [Bổ sung tên/số nhóm]
- Repository/branch: https://github.com/nhhung18/K4-L3A-RAG-Pipeline — `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Data — tài liệu IELTS Writing | Chọn nguồn và bổ sung mã tải 3 tài liệu: Writing Band Descriptors Task 1, Task 2 và Academic Writing Sample Tasks; lưu bản gốc phục vụ dữ liệu đầu vào của nhóm. | `src/task1_collect_legal_docs.py`; 3 file trong `data/landing/legal/` | Đã tải; cần bổ sung đuôi `.pdf` |
| Data — bài viết hướng dẫn | Chọn 2 URL IELTS Writing Task 1/Task 2 từ IDP; bổ sung logic crawl bằng Crawl4AI và lưu JSON gồm `url`, `title`, `date_crawled`, `content_markdown`. | `src/task2_crawl_news.py` | Đã bổ sung mã; chưa có JSON đầu ra để xác nhận crawl thành công |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Chọn bộ tiêu chí chấm điểm và đề mẫu IELTS Writing làm dữ liệu nguồn, bổ sung bài hướng dẫn từ IDP.  
   **Lý do/evidence:** Danh sách nguồn trong hai script tập trung vào Task 1 và Task 2, phù hợp chủ đề hỏi đáp của nhóm.  
   **Trade-off:** Phạm vi dữ liệu còn hẹp; 2 URL bài viết chưa đạt yêu cầu tối thiểu 5 bài/page.

2. **Quyết định:** Lưu tài liệu tải về ở dạng gốc và thiết kế đầu ra bài viết dưới dạng JSON có metadata nguồn.  
   **Lý do/evidence:** Task 1 lưu nội dung tải về trong `data/landing/legal/`; Task 2 có logic lưu từng bài vào `data/landing/news/`, giữ URL để bước chuẩn hóa có thể truy vết nguồn.  
   **Trade-off:** Cần kiểm tra định dạng file và chất lượng nội dung crawl trước khi chuyển giao cho bước chuẩn hóa.

## Kiểm thử và kết quả

- **Kiểm tra khi hoàn thiện báo cáo:** Đối chiếu mã nguồn và dữ liệu hiện có; cả 3 file `task-1-writing`, `task-2-writing`, `sample-tests` đều không rỗng và có chữ ký đầu file `%PDF-`.
- **Kết quả:** Có 3 file PDF gốc; chưa có JSON bài viết trong `data/landing/news/`. Chưa có số liệu trước/sau hoặc kết quả evaluation riêng cho phần thu thập dữ liệu.
- **Lỗi phát hiện và hướng xử lý:** Ba file tải về thiếu đuôi `.pdf`, trong khi Task 3 lọc theo phần mở rộng nên sẽ bỏ qua chúng. Cần sửa tên đầu ra trong Task 1 và bổ sung đuôi cho các file hiện có; lỗi này chưa được sửa tại thời điểm lập báo cáo.

## Điều còn hạn chế

- Bộ bài viết mới có 2 URL, chưa đủ số lượng và chưa có bằng chứng crawl thành công.
- Ưu tiên tiếp theo: sửa đuôi file PDF để bước chuẩn hóa nhận được dữ liệu; sau đó bổ sung ít nhất 3 URL phù hợp, chạy crawl và kiểm tra JSON có nội dung cùng metadata đầy đủ.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Trần Quốc Bảo Long
