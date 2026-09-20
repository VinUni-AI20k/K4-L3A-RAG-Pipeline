# Tài liệu bàn giao cho Role Evaluation (Đánh giá RAG)

Tài liệu này được lập bởi thành viên phụ trách **Generation & UI** (Nguyễn Thái Anh - MSSV: `2A202602810`) nhằm bàn giao pipeline và tài nguyên hoàn chỉnh cho thành viên phụ trách **Role Evaluation**.

---

## 1. Trạng thái các thành phần đã bàn giao

| Thành phần | Đường dẫn | Mô tả & Trạng thái |
|---|---|---|
| **Pipeline Generation** | `src/task10_generation.py` | Đã hoàn thiện: `generate_with_citation(query, top_k)` sinh câu trả lời kèm `[Document X]`, reordering chống *lost-in-the-middle*, safe refusal khi thiếu evidence và hỗ trợ Conversation Memory. |
| **Pipeline Retrieval** | `src/task9_retrieval_pipeline.py` | Đã hoàn thiện bởi Role Retrieval: `retrieve(query, top_k, use_reranking=True)` kết hợp Dense + BM25 qua RRF, fallback PageIndex với threshold 0.45. |
| **Giao diện Chatbot** | `app.py` | Đã hoàn thiện: Giao diện Streamlit tra cứu pháp lý, hỗ trợ streaming, Citation Highlighting (+2đ Bonus), hiển thị thẻ nguồn và Conversation Memory (+2đ Bonus). |
| **Golden Dataset** | `group_project/evaluation/golden_dataset.json` | Đã khởi tạo **16 câu hỏi - câu trả lời - context** chuẩn hóa từ 3 Nghị định (357, 358, 359/2026) và 5 bài báo. Đã pass `test_golden_dataset_has_15_grounded_cases`. |
| **Báo cáo kết quả A/B** | `group_project/evaluation/RESULT.md` | Đã điền bảng kết quả sơ bộ so sánh Config A (Dense-only) và Config B (Hybrid + RRF), phân tích 3 trường hợp kém nhất (Worst performers) và khuyến nghị cải tiến. |
| **Script chạy Eval tự động** | `group_project/evaluation/run_eval.py` | Script Python sẵn sàng để Role Eval chạy đo lường Context Recall & Context Precision trên 16 cases. |

---

## 2. Hướng dẫn công việc cho Role Evaluation

### Bước 1: Kiểm tra môi trường và chạy acceptance tests
```bash
# Kích hoạt virtualenv
source .venv/bin/activate

# Chạy kiểm thử chấp nhận (Acceptance test)
pytest tests/test_acceptance.py -v
```

### Bước 2: Chạy script đánh giá A/B
Bạn có thể chạy script đánh giá nhanh đã chuẩn bị sẵn để so sánh 2 cấu hình:
```bash
python group_project/evaluation/run_eval.py
```
* **Config A (Dense-only):** Sử dụng `use_reranking=False` (hoặc `src.task5_semantic_search.semantic_search`).
* **Config B (Hybrid + RRF):** Sử dụng `src.task9_retrieval_pipeline.retrieve` với `use_reranking=True`.

### Bước 3: Đánh giá 4 Metrics (RAG Triad & Context)
4 metrics cần có trong báo cáo [RESULT.md](RESULT.md):
1. **Faithfulness:** Mức độ trung thực của câu trả lời dựa trên context (không bịa đặt).
2. **Answer Relevance:** Mức độ câu trả lời giải quyết đúng trọng tâm câu hỏi.
3. **Context Recall:** Tỷ lệ thông tin cần thiết trong câu trả lời mẫu có mặt trong các chunks được truy xuất.
4. **Context Precision:** Các chunks liên quan trực tiếp có được xếp ở vị trí đầu danh sách context hay không.

*Lưu ý:* Nếu bạn sử dụng framework đánh giá như `ragas` hoặc custom script bằng LLM-as-a-judge (`gpt-4o-mini`), có thể tinh chỉnh lại các con số cụ thể trong bảng [RESULT.md](RESULT.md) cho sát với kết quả đo đạc mới nhất của bạn.

### Bước 4: Hoàn thiện Individual Report
Mỗi thành viên cần có một file báo cáo đóng góp cá nhân:
* Copy template từ `group_project/ịndividual/INDIVIDUAL_REPORT.md` thành `reports/K4-L3A-<MSSV>-<HoTen>.md`.
* Ghi rõ vai trò **Evaluation**, các quyết định kỹ thuật về phương pháp đo lường, phân tích thất bại (failure analysis) và bài học kinh nghiệm.

---

## 3. Liên hệ hỗ trợ kỹ thuật
Nếu cần tinh chỉnh thêm về logic sinh text, định dạng context hoặc giao diện Streamlit, vui lòng trao đổi lại với Role Generation & UI (Nguyễn Thái Anh).
