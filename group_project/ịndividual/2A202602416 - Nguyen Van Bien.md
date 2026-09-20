# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Văn Biển
- Mã học viên: 2A202602416
- Nhóm: Track C — Generation, Product & Evaluation
- Repository/branch: `NguyenVanBien-02416`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 10 — Generation có citation | Thiết kế toàn bộ pipeline sinh câu trả lời: `reorder_for_llm()` chống lost-in-the-middle, `format_context()` gắn label [Document N], `call_llm()` đa provider (OpenAI/Gemini/Anthropic), `generate_with_mode()` cho A/B test retrieval, `generate_with_history()` + `rewrite_standalone_query()` cho conversation memory (bonus). | `src/task10_generation.py` | Done |
| Chatbot Streamlit (`app.py`) | Xây dựng UI end-to-end: highlight citation badge màu (`highlight_citations()`), sidebar chọn `top_k` và retrieval mode (dense vs hybrid), demo seed 3 câu khởi động, `render_sources()` với expander kèm score và snippet 300 ký tự, hiển thị standalone query khi rewrite khác câu gốc. | `app.py` | Done |
| Golden dataset | Thiết kế và biên soạn 15 câu hỏi đa dạng (legal + news, dễ/khó, in-domain/out-of-domain) với `expected_answer` và `expected_context` có thể đối chiếu trực tiếp với văn bản nguồn. | `group_project/evaluation/golden_dataset.json` | Done |
| Evaluation pipeline — 4 metrics | Viết `run_eval.py`: so sánh kiểm soát biến Config A (dense-only) vs Config B (hybrid+RRF), đánh giá 4 metric ragas (Faithfulness, AnswerRelevancy, ContextRecall, ContextPrecision), ghi kết quả thô theo từng câu để không mất tiến độ khi bị gián đoạn. | `group_project/evaluation/run_eval.py` | Done |
| Bonus — HyDE & LLM Reranker | Viết `run_eval_bonus.py`: thử nghiệm HyDE (sinh hypothetical document rồi embed) và LLM Reranker (chấm điểm 0-10 từng candidate sau RRF), chạy song song bằng asyncio, kết luận HyDE fix hoàn toàn worst-case #1 (recall 0.0 → 1.0). | `group_project/evaluation/run_eval_bonus.py` | Done |
| RESULT.md | Tổng hợp bảng điểm 4 metric 2 config, phân tích 3 worst performers, đề xuất 3 recommendations ưu tiên, kết luận bonus experiments với trade-off latency/cost. | `group_project/evaluation/RESULT.md` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng `reorder_for_llm()` xen kẽ front/back thay vì giữ thứ tự RRF để đưa chunks quan trọng về đầu và cuối context.  
   **Lý do/evidence:** Nghiên cứu "Lost in the Middle" (Liu et al. 2023) chỉ ra LLM bỏ qua thông tin ở giữa context dài; bằng cách tách front (`chunks[::2]`) và back (`chunks[1::2][::-1]`), cả hai đầu đều nhận chunks có rank cao nhất, giữ context ngữ nghĩa mà không cần thêm LLM call.  
   **Trade-off:** Thứ tự hiển thị nguồn (`[Document N]`) không còn khớp hoàn toàn với thứ tự RRF score — người dùng có thể nhầm khi đọc citation; giải pháp là giữ mapping rõ ràng trong `format_context()` với label tiêu đề và source.

2. **Quyết định:** Thiết kế golden dataset với 3 nhóm khó (định danh số hiệu văn bản + khái niệm, near-miss top_k, data quality), so sánh A/B kiểm soát biến duy nhất là retrieval strategy.  
   **Lý do/evidence:** Kết quả A/B cho thấy hybrid thắng rõ ở context recall (+0.133) nhờ BM25 bù câu hỏi có định danh cụ thể, trong khi faithfulness giảm nhẹ (−0.047) vì BM25 đẩy nhầm 1 chunk nhiễu — phát hiện này dẫn trực tiếp đến bonus HyDE, fix case #1 recall 0.0 → 1.0.  
   **Trade-off:** 15 câu là tập nhỏ (n nhỏ, biên độ nhiễu lớn), kết luận mang tính tham khảo chứ không mang tính thống kê tuyệt đối; cần mở rộng golden dataset lên 50+ câu nếu muốn kết quả robust hơn.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  + Chạy toàn bộ evaluation: `python -m group_project.evaluation.run_eval` — 15 câu × 2 config = 30 lượt generate + score.
  + Demo seed 3 câu đặc trưng trực tiếp qua Streamlit UI: câu hỏi in-domain (thuế hộ kinh doanh), câu có số hiệu văn bản (NQ 198), câu out-of-domain (hàm số bậc hai).
  + Bonus: `python -m group_project.evaluation.run_eval_bonus` — HyDE và LLM Reranker trên cùng 15 câu.
- Kết quả trước/sau nếu có:
  + Hybrid+RRF baseline: Average **0.761** (dense-only: 0.729).
  + Sau HyDE: Average **0.808** (+0.047); case #1 worst performer context recall **0.0 → 1.0** (fix hoàn toàn).
  + Sau LLM Reranker: Average **0.825** (+0.064, cao nhất), nhưng case #1 vẫn recall=0.0 (reranker không tạo candidate mới).
- Lỗi đã phát hiện và cách xử lý: `safe_score()` wrapper bắt exception khi ragas metric lỗi (timeout, JSON parse fail) và trả `None` thay vì crash toàn bộ run; kết quả thô ghi từng câu ngay vào file JSON để khởi động lại không mất tiến độ.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Golden dataset chỉ có 15 câu, tập trung vào domain pháp luật hộ kinh doanh — `answer_relevancy` đạt thấp (~0.48) một phần vì metric ragas đo bằng cosine similarity giữa câu hỏi và câu trả lời embed, dễ bị ảnh hưởng bởi văn phong hành chính lặp từ ("quy định", "hộ kinh doanh") làm nhiễu embedding.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Kết hợp HyDE và LLM Reranker thành một pipeline duy nhất (HyDE → RRF → LLM Reranker) để tận dụng cả ưu điểm cải thiện recall của HyDE và cải thiện precision của LLM Reranker; dự kiến average có thể vượt 0.85.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20-09-2026
- Tên thành viên: Nguyễn Văn Biển
