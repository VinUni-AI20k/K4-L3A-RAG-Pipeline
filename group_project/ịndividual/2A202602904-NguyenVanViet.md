# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Văn Việt
- Mã học viên: 2A202602904
- Nhóm: K4-L3A
- Repository/branch: tài khoản github: little-duck-vie, branch: viet

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm                                     | File/commit/PR                         | Trạng thái |
| ------------------ | --------------------------------------------------------------- | -------------------------------------- | ------------ |
| Task 2: Crawl News | Viết code cào tin tức tuyển sinh từ web trường PTIT.     | `src/task2_crawl_news.py`            | Done         |
| Task 8: Evaluation | Chạy script tự động chấm điểm 4 metric và so sánh A/B. | `group_project/evaluation/RESULT.md` | Done         |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Sử dụng thư viện `crawl4ai` thay vì code BeautifulSoup chay.
   **Lý do/evidence:** Gói này nó gom sẵn thành markdown gọn gàng luôn, đỡ phải xử lý mấy cái thẻ HTML lằng nhằng rác rưởi.
   **Trade-off:** Cài đặt thư viện này tải hơi lâu và nặng máy.
2. **Quyết định:** Chấm điểm dùng `gpt-4o-mini` làm giám khảo.
   **Lý do/evidence:** Rẻ, chạy nhanh mà kết quả đánh giá vẫn khá ổn, sinh viên dùng API đỡ xót tiền.
   **Trade-off:** Vài câu khó nó chấm điểm hơi ngáo, không tinh tế bằng con gpt-4 xịn.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: Chạy file đánh giá xuất ra file `RESULT.md`.
- Kết quả trước/sau nếu có: Bản Hybrid (RRF) điểm cao hơn bản Dense-only hẳn 0.05 điểm trung bình.
- Lỗi đã phát hiện và cách xử lý: Lúc cào web bị lỗi dính mấy cái script với footer, em chỉnh lại thẻ CSS selector trong crawl4ai là nó sạch sẽ ngay.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Cào tin mới chỉ lấy chữ chứ mất sạch hình ảnh minh họa, đọc hơi chán.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Code thêm chỗ lưu log các lần test lại thành file csv để tiện vẽ biểu đồ so sánh cho chuyên nghiệp.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Văn Việt
