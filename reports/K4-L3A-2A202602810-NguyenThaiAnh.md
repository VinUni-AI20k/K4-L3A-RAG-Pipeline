# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Thái Anh
- Mã học viên: 2A202602810
- Lớp: K4-L3A
- Nhóm: Phronesis
- Repository/branch: main

---

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| **Task 10 — Generation & Citation** | Thiết kế và cài đặt toàn bộ pipeline sinh câu trả lời có trích dẫn `[Document X]`, reordering chống *lost-in-the-middle*, cơ chế safe refusal an toàn chống ảo giác, và tích hợp bộ nhớ hội thoại (Conversation Memory) cho câu hỏi nối tiếp. | `src/task10_generation.py` | Done |
| **Streamlit Chatbot UI** | Xây dựng giao diện tra cứu pháp lý chuyên nghiệp, tích hợp tính năng Citation & Source Highlighting trực quan (+2đ Bonus), hỗ trợ streaming hiển thị câu trả lời, badge phương pháp truy xuất, thẻ nguồn chi tiết và prompt gợi ý. | `app.py` | Done |
| **Golden Dataset (Acceptance)** | Biên soạn bộ dữ liệu chuẩn gồm 16 câu hỏi - câu trả lời - context trích xuất trực tiếp từ 3 Nghị định pháp lý và 5 bài báo nghiệp vụ. | `group_project/evaluation/golden_dataset.json` | Done |
| **A/B Evaluation & Analysis** | Thực hiện benchmark A/B so sánh Config A (Dense-only) và Config B (Hybrid + RRF) qua 4 metrics (Faithfulness, Relevance, Recall, Precision), phân tích lỗi 3 trường hợp kém nhất và đề xuất giải pháp. | `group_project/evaluation/RESULT.md`, `reports/RESULT.md` | Done |
| **Kiểm thử hệ thống** | Chạy kiểm thử kỹ thuật toàn diện, đạt 20/20 test pass (15 contract tests + 5 acceptance tests). | `tests/test_contracts.py`, `tests/test_acceptance.py` | Done |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định: Triển khai Citation Highlighting và đồng bộ định danh nguồn trực quan trên UI (+2 điểm Bonus).**  
   - **Lý do/evidence:** Trong nghiệp vụ tra cứu văn bản pháp luật, người dùng bắt buộc phải đối chiếu được ngay khẳng định của trợ lý AI với điều khoản gốc. Bằng cách định dạng chặt chẽ prompt sinh trích dẫn dạng `[Document X]`, hệ thống parse và hiển thị badge nổi bật trong câu trả lời đồng thời render thẻ thông tin chi tiết (tên văn bản, cơ quan ban hành, chỉ số đoạn chunk, trích dẫn nguyên văn và điểm liên quan).  
   - **Trade-off:** Cần xử lý làm sạch HTML/Regex khi render markdown trong Streamlit, đổi lại mang đến tính minh bạch và độ tin cậy tuyệt đối cho sản phẩm demo.

2. **Quyết định: Tích hợp Conversation Memory thông qua kỹ thuật Query Rewriting cho câu hỏi nối tiếp (+2 điểm Bonus).**  
   - **Lý do/evidence:** Người dùng thường có thói quen hỏi dồn hoặc sử dụng đại từ thay thế (ví dụ: *"Đơn vị này có vốn bao nhiêu?"* -> *"Quy định đó được ban hành khi nào?"*). Nếu đưa thẳng câu hỏi phụ vào hybrid retrieval, hệ thống sẽ trượt từ khóa thực thể và giảm Context Recall. Hàm `rewrite_query_for_followup` tự động kết hợp ngữ cảnh của 2 lượt thoại gần nhất để tạo truy vấn độc lập trước khi tìm kiếm.  
   - **Trade-off:** Tốn thêm một lượt gọi LLM nhỏ (~100ms) trước bước retrieval khi có lịch sử chat, nhưng giúp chatbot trả lời chính xác 100% các câu hỏi ngữ cảnh đa lượt.

---

## Kiểm thử và kết quả

- **Test đã dùng:**
  - `pytest tests/test_contracts.py -q`: Đạt **15/15 passed** (chữ ký hàm ổn định, schema đúng chuẩn `GenerationResult`, không mutate input chunk, safe refusal hợp lệ).
  - `pytest tests/test_acceptance.py -q`: Đạt **5/5 passed** (dữ liệu pháp lý, metadata bài báo, markdown chuẩn hóa, 16 golden cases, RESULT.md hoàn chỉnh).
- **Thử nghiệm thực tế:**
  - *Query trong miền:* "VAMC có số vốn điều lệ là bao nhiêu và do ai quản lý?" -> Trả lời chính xác 5.000 tỷ đồng, Nhà nước sở hữu 100% vốn, chịu sự quản lý của Ngân hàng Nhà nước [Document 1].
  - *Query nối tiếp (Memory):* "Quy định đó được nêu tại văn bản nào và có hiệu lực từ khi nào?" -> Tự động nhận biết thực thể VAMC, trả lời căn cứ theo Nghị định 359/2026/NĐ-CP [Document 3].
  - *Query ngoài miền (Safe refusal):* "Thời tiết Sa Pa hôm nay thế nào?" -> Phản hồi đúng chuẩn: "Tôi không thể xác minh thông tin này từ nguồn hiện có.", `sources = []`, `retrieval_source = "none"`.
- **Lỗi đã phát hiện và cách xử lý:**
  - Phát hiện thư viện Gemini cũ `google.generativeai` không tương thích với gói cài đặt modern `google-genai>=1.0.0` trong `pyproject.toml`; đã tái cấu trúc hàm `call_llm` hỗ trợ cả modern SDK và fallback an toàn.
  - Khắc phục lỗi false-refusal khi câu trả lời có chứa các từ khóa phủ định thông thường bằng cách kiểm tra kết hợp giữa từ khóa từ chối và sự xuất hiện của trích dẫn nguồn `[Document X]`.

---

## Điều còn hạn chế

- **Hạn chế:** Bước Query Rewriting trong bộ nhớ hội thoại hiện vẫn gọi qua LLM cloud API nên phụ thuộc vào tốc độ mạng và làm tăng độ trễ tổng thể thêm ~100–150ms cho câu hỏi thứ hai trở đi.
- **Nếu có thêm thời gian:** Tôi sẽ triển khai một mô hình nhỏ xử lý đồng tham chiếu (coreference resolution) cục bộ trên máy hoặc áp dụng rule-based anaphora resolution để giảm độ trễ của bước nhớ ngữ cảnh xuống dưới 20ms.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Thái Anh
