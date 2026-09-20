# Individual Contribution Report

---

## Thông tin

- **Họ và tên:** Ngụy Quang Hùng
- **Mã học viên:** 2A202602998
- **Nhóm:** K4-L3A
- **Repository/branch:** K4-L3A-RAG-Pipeline-MegaLive / quanghung (github user: diggoryQH)

---

## Phần việc đã thực hiện

| Module/deliverable                | Việc tôi trực tiếp làm                                                                                                | File/commit/PR                      | Trạng thái |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | ------------ |
| Thu thập tài liệu PDF (Task 1) | Lên web PTIT tải 3 file điểm chuẩn, học phí, thông báo tuyển sinh bản PDF vào thư mục`data/landing/legal/` | `src/task1_collect_legal_docs.py` | Hoàn thành |
| Thuật toán RRF (Task 7)         | Code hàm`rerank_rrf()` nhận list kết quả của Dense và BM25, cộng điểm theo công thức `1 / (k + rank)`       | `src/task7_reranking.py`          | Hoàn thành |
| Unit Test RRF                     | Chạy pytest để test hàm RRF trả về đúng chuẩn, đảm bảo không bị trùng ID giữa 2 list kết quả             | `tests/test_contracts.py`         | Hoàn thành |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Tải PDF bằng tay thay vì code tool tự tải.
   **Lý do/evidence:** Website của trường hay chặn script crawl, link file PDF lại không có API cố định. Có đúng 3 file văn bản pháp lý quan trọng nhất nên tôi quyết định tải tay lưu vào thư mục cho an toàn, tránh lỗi mạng ảnh hưởng cả dự án.
   **Trade-off:** Sẽ không thể tự động update có file mới nếu trường ra công văn sửa đổi đột xuất.
2. **Quyết định:** Chọn thông số k=60 làm mặc định cho thuật toán RRF.
   **Lý do/evidence:** Vì bộ dữ liệu bài tập lớn của nhóm khá nhỏ, tôi dùng k=60 theo kinh nghiệm cấu hình phổ biến trên mạng. Chạy test A/B thử thấy có cải thiện điểm.
   **Trade-off:** Chưa có thời gian để viết vòng lặp test dò tìm tham số k tối ưu nhất cho riêng bộ dữ liệu này.

---

## Kiểm thử và kết quả

- **Test đã dùng:** Chạy lệnh `pytest tests/test_contracts.py -q -k "rerank"`
- **Kết quả:** Code RRF chạy pass, giúp nâng điểm Faithfulness của hệ thống từ 0.69 (chỉ dùng Dense) lên 0.79.
- **Lỗi đã phát hiện và cách xử lý:** Lúc đầu code bị lỗi khi có cùng một đoạn văn (chunk) xuất hiện ở cả kết quả Dense và BM25 thì điểm bị tính đè lên nhau sai. Đã sửa lại code để gom nhóm các ID trùng lặp lại trước khi cộng dồn tổng điểm.

---

## Điều còn hạn chế

- Việc kết hợp Dense và BM25 hiện tại đang bắt chương trình chạy tuần tự từng cái một nên thời gian truy vấn bị chậm đi một chút.
- Nếu có thời gian, thay đổi đầu tiên tôi sẽ làm là cấu hình thêm thư viện async để 2 cục tìm kiếm chạy song song rồi mới dùng RRF gom lại, sẽ tối ưu được tốc độ.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- **Ngày:** 2026-09-20
- **Tên thành viên:** Ngụy Quang Hùng
