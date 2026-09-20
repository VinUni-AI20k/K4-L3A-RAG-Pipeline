# Individual contribution report

## Thông tin

- Họ và tên: Nguỵ Quang Hùng
- Mã học viên: 2A202602998
- Nhóm: K4-L3A
- Repository/branch:  tài khoản github: diggoryQH

## Phần việc đã thực hiện

| Module/deliverable    | Việc tôi trực tiếp làm                                        | File/commit/PR                   | Trạng thái |
| --------------------- | ------------------------------------------------------------------ | -------------------------------- | ------------ |
| Task 1: Collect Legal | Tìm kiếm và tải mấy file PDF quy chế tuyển sinh, học phí. | Thư mục`data/landing/legal/` | Done         |
| Task 7: Fallback      | Bắt lỗi nếu user hỏi linh tinh thì chatbot phải chặn lại.  | `src/task7_fallback.py`        | Done         |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Lấy dữ liệu tuyển sinh chính thức năm 2026 của PTIT từ trang web trường.
   **Lý do/evidence:** Nguồn chính thống nhất, sinh viên hay thắc mắc về điểm chuẩn và học phí nên em gom 3 file PDF này.
   **Trade-off:** Dữ liệu khá ít và ngắn nên pipeline xử lý nhàn, nhưng test mở rộng thì khó.
2. **Quyết định:** Set cái `SCORE_THRESHOLD = 0.3` để làm fallback.
   **Lý do/evidence:** Test thử thấy dưới 0.3 toàn là mấy kết quả không liên quan gì đến câu hỏi.
   **Trade-off:** Nhiều lúc người dùng hỏi hơi tắt, điểm cosine thấp một xíu bị chặn nhầm luôn không thèm trả lời.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: Thử gõ mấy câu kiểu "thời tiết hôm nay thế nào", "tối nay ăn gì".
- Kết quả trước/sau nếu có: Lúc đầu bot vẫn ráng chém gió từ thông tin tuyển sinh, sau khi ép threshold vào thì nó báo lỗi gọn gàng "không xác minh được thông tin".
- Lỗi đã phát hiện và cách xử lý: Lỗi để file dummy quá ngắn làm fail test, em đã fix bằng cách xóa file dummy đi chỉ xài đồ thật.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Tải file PDF toàn làm bằng tay, bấm nút download thủ công.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Viết hẳn tool tự động chui vào trang PTIT tải hết PDF về cho xịn xò.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguỵ Quang Hùng
