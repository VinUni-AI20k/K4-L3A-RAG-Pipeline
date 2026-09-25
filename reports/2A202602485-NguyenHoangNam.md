# Individual contribution report

---

## Thông tin

- Họ và tên: Nguyễn Hoàng Nam
- Mã học viên: 2A202602485
- Nhóm: 5changlinhngulam
- Repository/branch: [github.com/AIVIETNAM-AIO-AnhDinh/K4-L3B-RAG-Pipeline.git](https://github.com/AIVIETNAM-AIO-AnhDinh/K4-L3B-RAG-Pipeline.git) / nhánh nam2

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm                                                                                                          | File/commit/PR                          | Trạng thái |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------- | ------------ |
| Task 7: Reranking  | Implement thuật toán Reciprocal Rank Fusion (RRF) để kết hợp kết quả từ Semantic Search và Lexical Search.                 | `src/task7_reranking.py`              | Done         |
| Task 8: PageIndex  | Implement fallback bằng PageIndex API: tự động render PDF, xử lý cache document ID, multi-threading query, parse node content. | `src/task8_pageindex_vectorless.py`   | Done         |
| Fix Git Conflicts  | Xử lý lỗi unrelated histories khi merge từ nhánh main sang nhánh cá nhân.                                                    | Commit`09a8c3d` (Merge branch 'main') | Done         |

## Quyết định kỹ thuật quan trọng

Mô tả tối đa hai quyết định mà bạn trực tiếp tham gia:

1. **Quyết định:** Sử dụng `ThreadPoolExecutor` để query đồng thời các tài liệu thay vì gọi tuần tự đối với PageIndex API trong Task 8.**Lý do/evidence:** API của PageIndex yêu cầu submit query và dùng cơ chế polling (liên tục kiểm tra trạng thái). Với nhiều tài liệu, việc query tuần tự sẽ rất chậm và làm bottleneck toàn bộ hệ thống RAG. Việc dùng concurrency (tối đa 4 workers) giảm đáng kể độ trễ.
   **Trade-off:** Cần xử lý cẩn thận timeout và bắt các lỗi phát sinh ở các luồng (thread) độc lập để không làm gián đoạn toàn bộ các query khác.
2. **Quyết định:** Áp dụng caching cục bộ (`pageindex_doc_ids.json`) thay vì luôn luôn upload lại tài liệu lên PageIndex API.
   **Lý do/evidence:** Quá trình upload PDF qua API tốn nhiều băng thông, thời gian, và không cần thiết với các tài liệu tĩnh không đổi. Việc lưu `doc_id` tương ứng với mỗi file giúp tiết kiệm chi phí và tài nguyên mạng cho những lần run tiếp theo.
   **Trade-off:** Cần cơ chế lưu trữ file json local; nếu metadata hoặc file nguồn thay đổi nhưng file json chưa cập nhật (cache invalidation) thì dữ liệu có thể bị cũ.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: Thử nghiệm query `Người mua có bao nhiêu ngày để yêu cầu trả hàng?` đối với hàm `rerank_rrf` sau khi merge với `semantic_search` và `lexical_search`.
- Kết quả trước/sau nếu có: RRF xử lý gộp kết quả tốt, hạn chế việc điểm của một mô hình áp đảo phương pháp kia, tạo rank mới tổng hòa được nhiều tín hiệu.
- Lỗi đã phát hiện và cách xử lý: Không có timeout mặc định từ SDK của PageIndex. Đã khắc phục bằng cách thiết lập cờ `deadline = time.monotonic() + PAGEINDEX_TIMEOUT` và catch Exception trong Python để không sập script tìm kiếm.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: PageIndex phụ thuộc hoàn toàn vào dịch vụ bên thứ 3. Nếu API có lỗi từ server, pipeline bắt buộc phải chuyển sang fallback, dù đôi khi chỉ là lỗi mạng tạm thời (chưa implement retry exponential backoff).
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Bổ sung logic thử lại (retry logic) nâng cao cho các API call lỗi, và cơ chế cache invalidation tự động dựa trên mã băm (hash) của file gốc thay vì đường dẫn tĩnh.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Tên thành viên: Nguyễn Hoàng Nam
