# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Hải Long
- Mã học viên: 2A202602471
- Nhóm: GICUNGDC
- Repository/branch: https://github.com/thangws4/K4-Day08-GICUNGDC / nhánh `long2711`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 8 — PageIndex Vectorless Fallback | Hiện thực hàm tìm kiếm dự phòng không dùng vector dựa trên chỉ mục trang, xử lý ngoại lệ an toàn | `src/task8_pageindex_vectorless.py` | Done |
| Task 9 — Retrieval Pipeline Orchestrator | Xây dựng pipeline điều phối truy xuất Hybrid RRF, tích hợp điều kiện kích hoạt Fallback khi điểm dense thấp hoặc provider lỗi | `src/task9_retrieval_pipeline.py` | Done |
| Task 10 — Generation with Citation | Xây dựng module sinh phản hồi với Gemini, định dạng context giảm Lost-in-the-middle, gắn citation `[Document X]` và safe refusal | `src/task10_generation.py` | Done |
| User Interface & REST API | Xây dựng giao diện tương tác Streamlit `app.py`, phát triển Fullstack Vercel AI Chatbot Dark Mode và server FastAPI | `app.py`, `api_server.py`, `frontend/` | Done |

## Quyết định kỹ thuật quan trọng

Mô tả tối đa hai quyết định mà bạn trực tiếp tham gia:

1. **Quyết định:** Thiết kế cơ chế điều phối phân tầng (Orchestration) và Safe Fallback trong Task 8 & 9.  
   **Lý do/evidence:** Hệ thống vector database có thể suy giảm độ chính xác khi câu hỏi chứa từ khóa cấu trúc hoặc khi provider embedding gặp sự cố tạm thời. Khi điểm tương đồng dense < ngưỡng tin cậy (`FALLBACK_THRESHOLD`), hệ thống tự động kích hoạt fallback sang PageIndex vectorless mà không làm sập luồng xử lý.  
   **Trade-off:** Có thể tăng nhẹ thời gian truy xuất khi kích hoạt luồng fallback, nhưng đảm bảo 100% tính sẵn sàng (fault-tolerance) và vượt qua toàn bộ các contract test về fallback resilience.

2. **Quyết định:** Tái sắp xếp ngữ cảnh (Context Reordering) và Citation Grounding nghiêm ngặt trong Task 10.  
   **Lý do/evidence:** Mô hình ngôn ngữ lớn (LLM) thường gặp hiện tượng "Lost in the middle" (chỉ chú ý đầu và cuối prompt). Bằng cách xếp các chunk điểm cao nhất ở đầu và cuối context, kết hợp ép prompt chỉ trả lời từ evidence có trích dẫn số hiệu `[Document X]`, hệ thống triệt tiêu hoàn toàn hiện tượng ảo giác (hallucination) trong tư vấn Luật Giao thông.  
   **Trade-off:** Chấp nhận trả về câu từ chối an toàn (*Safe Refusal*) khi dữ liệu không đủ bằng chứng thay vì để LLM tự suy diễn.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: `pytest tests/test_contracts.py -q`, `pytest tests/test_acceptance.py -q`, `pytest -q`.
- Kết quả trước/sau nếu có: Đạt **20/20 test cases passed (100%)**.
- Lỗi đã phát hiện và cách xử lý: Khắc phục lỗi client closed exception khi khởi tạo Gemini Client bằng cách khởi tạo `genai.Client(api_key=api_key)` tường minh trong `task10_generation.py`, giúp LLM sinh đầy đủ nội dung kèm citation thay vì rơi vào fallback từ chối sai lệch.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Ngưỡng fallback hiện tại đang cấu hình tĩnh (`0.5`); đối với các truy vấn rất ngắn hoặc từ đồng nghĩa phức tạp có thể cần cơ chế adaptive threshold.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Bổ sung lớp Re-ranking sử dụng Cross-Encoder (như `bge-reranker-large`) trước khi đưa context vào Task 10 và tích hợp streaming response trên giao diện Web UI.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Hải Long
