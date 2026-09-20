# Individual Contribution Report

---

## Thông tin

- **Họ và tên:** Nguyễn Văn Việt
- **Mã học viên:** 2A202602904
- **Nhóm:** K4-L3A — RAG Pipeline PTIT
- **Repository/branch:** K4-L3A-RAG-Pipeline-MegaLive / main

---

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
| ------------------ | ----------------------- | -------------- | ---------- |
| Crawl tin tức (Task 2) | Viết script dùng Crawl4AI thu thập 5 bài viết về tuyển sinh từ web trường, lưu thành file JSON có metadata | `src/task2_crawl_news.py` | Hoàn thành |
| Cài đặt PageIndex (Task 8)| Viết module gọi API ngoài của PageIndex để mở rộng phương thức tìm kiếm bổ sung cho RAG | `src/task8_pageindex_vectorless.py` | Hoàn thành |
| Xử lý Fallback | Code `try/except` để bắt lỗi khi hệ thống PageIndex sập, đảm bảo bot vẫn chạy bình thường trả mảng rỗng | `src/task8_pageindex_vectorless.py` | Hoàn thành |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng Crawl4AI thay vì Beautiful Soup để cào dữ liệu.
   **Lý do/evidence:** Mấy trang tin tức của PTIT bây giờ có nhiều chỗ dùng JavaScript để load nội dung (lazy load). Dùng Crawl4AI (tự chạy ngầm Playwright) giúp cào được toàn bộ nội dung mà lại tự động convert ra Markdown khá sạch sẽ.
   **Trade-off:** File cài đặt dự án nặng hơn nhiều vì phải kéo theo trình duyệt Chromium, lúc ấn chạy crawl lần đầu cũng tốn nhiều thời gian hơn.

2. **Quyết định:** Để fallback trả về mảng trống thay vì báo lỗi đỏ màn hình khi API chết.
   **Lý do/evidence:** PAGEINDEX_API_KEY chưa được thầy cấp, nên hiện tại khi gọi chắc chắn sẽ bị lỗi báo về. Tôi bắt exception ngay trong hàm search để pipeline chính của cả nhóm không bị dừng đột ngột.
   **Trade-off:** Module task 8 hiện đang giống như chỉ để làm mock, chưa đánh giá được hiệu quả thật sự của PageIndex trên bộ dữ liệu này.

---

## Kiểm thử và kết quả

- **Test đã dùng:** Chạy lệnh `pytest tests/test_contracts.py -q -k "pageindex"`
- **Kết quả:** Đã lấy được đủ 5 bài chuẩn về học phí và chỉ tiêu năm 2026. Hàm fallback hoạt động đúng như thiết kế khi bị lỗi API, giúp pipeline nhóm pass 100% test contract.
- **Lỗi đã phát hiện và cách xử lý:** Ban đầu lúc chạy crawl tự động bị đụng phải một số bài báo redirect vòng vòng tạo ra nội dung rác. Tôi phải viết thêm hàm check trùng lặp URL trước khi cho ghi đè file.

---

## Điều còn hạn chế

- 5 bài báo vẫn hơi mỏng để hệ thống RAG trả lời mượt mà mọi câu hỏi mở của sinh viên.
- Nếu có thời gian, thay đổi đầu tiên tôi làm là sẽ code luồng đệ quy để tự động vào các chuyên mục "Tuyển sinh" của trường rồi cào toàn bộ tin tức từ đầu năm đến giờ.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- **Ngày:** 2026-09-20
- **Tên thành viên:** Nguyễn Văn Việt
