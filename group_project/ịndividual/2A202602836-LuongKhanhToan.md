# Individual contribution report

## Thông tin

- Họ và tên: Lương Khánh Toàn
- Mã học viên: 2A202602836
- Nhóm: Team G36
- Repository/branch: main

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Retrieval Orchestration | Thiết kế pipeline phối hợp Hybrid (Dense + BM25), hợp nhất RRF 1 lần và fallback PageIndex an toàn khi score < threshold | `src/task9_retrieval_pipeline.py` | Done |
| Generation with Citations | Cài đặt reordering chống lost-in-the-middle, format context pháp lý có bằng chứng [E1], dispatch đa provider LLM và citation validation | `src/task10_generation.py` | Done |
| Chatbot Integration | Tích hợp RAG Pipeline end-to-end vào Streamlit, hiển thị căn cứ pháp lý, nguồn trích dẫn và điểm tương quan | `app.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Tách biệt kiểm tra threshold dựa trên Cosine score gốc của Dense thay vì dùng RRF score.  
   **Lý do/evidence:** RRF là thang đo nghịch đảo thứ hạng mang tính tương đối (1/(60+rank)), không phản ánh khoảng cách độ tương đồng ngữ nghĩa thực sự giữa query và corpus.  
   **Trade-off:** Phải giữ lại điểm số gốc của dense kết quả trước khi đưa vào hàm RRF, nhưng đảm bảo kích hoạt fallback PageIndex chính xác khi gặp query out-of-domain.

2. **Quyết định:** Áp dụng thuật toán Reorder (Lost-in-the-Middle) và bọc kiểm chứng trích dẫn (Citation Validation).  
   **Lý do/evidence:** Mô hình ngôn ngữ lớn thường chú ý tốt nhất ở đầu và cuối context. Trong nghiệp vụ tư vấn pháp lý về chất cấm/Pod, việc trích dẫn sai số hiệu điều luật gây hậu quả nghiêm trọng.  
   **Trade-off:** Tốn thêm một bước tiền xử lý context và hậu xử lý regex kiểm tra ID [E...], nhưng loại bỏ hoàn toàn việc mô hình bịa đặt citation ảo.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: `pytest tests/test_contracts.py -k "reorder or retrieve or generation"`, test query in-domain ("Hút pod chill chứa ma túy bị phạt thế nào?") và out-of-domain ("Công thức làm bánh mì").
- Kết quả trước/sau: Trước đó pipeline chưa tích hợp và chưa có giao diện Streamlit; sau khi hoàn thiện, chatbot chạy mượt mà end-to-end, trả về câu trả lời kèm nguồn căn cứ pháp luật rõ ràng, 100% tests contract pass.
- Lỗi đã phát hiện và cách xử lý: Phát hiện biến môi trường LLM_MODEL bị rỗng dẫn đến lỗi khởi tạo client; đã bổ sung fallback tự động về `gemini-3.5-flash-lite` và bọc try-except an toàn cho nhánh fallback.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Tốc độ phản hồi phụ thuộc vào độ trễ của API Gemini từ nhà cung cấp khi context dài.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Triển khai cơ chế Streaming response trên Streamlit để người dùng không phải chờ đợi toàn bộ câu trả lời được sinh xong.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Lương Khánh Toàn
