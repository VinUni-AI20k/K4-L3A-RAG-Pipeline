# RAG evaluation results

## Run information

| Field                              | Value |
| ----------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | ragas 0.4.3 (`ragas.metrics.collections`) |
| Evaluator model                    | `gpt-4o-mini` (OpenAI, qua `llm_factory`) |
| Generator model                    | `gpt-4o-mini` (OpenAI, qua `call_llm()` trong `task10_generation.py`) |
| Embedding model                    | `text-embedding-3-small` (OpenAI, `EMBEDDING_PROVIDER=openai` trong `.env`) |
| Corpus version/commit              | `63161ce` (nhánh `main`), 1716 chunks, 4 văn bản luật + 6 bài báo |
| Golden dataset size                | 15 câu (`group_project/evaluation/golden_dataset.json`) |
| `top_k`                            | 5 |
| Fallback threshold and calibration | `SCORE_THRESHOLD = 0.3` (hardcode trong `task9_retrieval_pipeline.py`, so với cosine score gốc của dense; `.env` có field cùng tên nhưng hiện chưa được đọc — cần Track B nối lại nếu muốn hiệu chỉnh qua `.env`) |

Script chạy: `python -m group_project.evaluation.run_eval` (kết quả thô lưu ở
`group_project/evaluation/eval_raw_results.json`).

## Configurations

- **Config A — dense-only:** `retrieve(query, top_k=5, use_reranking=False)` — chỉ `semantic_search()`, không fuse BM25.
- **Config B — hybrid + RRF:** `retrieve(query, top_k=5, use_reranking=True)` — `semantic_search()` + `lexical_search()` fuse bằng `rerank_rrf()` (k=60).

Hai config dùng cùng golden dataset, cùng generator (`gpt-4o-mini`), cùng evaluator, cùng system prompt (`task10_generation.SYSTEM_PROMPT`) và cùng `top_k=5`; chỉ khác retrieval strategy — đúng yêu cầu so sánh kiểm soát biến.

## Overall scores

| Metric            | Config A (dense) | Config B (hybrid) | Delta B−A |
| ----------------- | ---------------: | -----------------: | --------: |
| Faithfulness      |            0.900 |               0.853 |    −0.047 |
| Answer relevance  |            0.488 |               0.476 |    −0.012 |
| Context recall    |            0.733 |               0.867 |    +0.133 |
| Context precision |            0.794 |               0.847 |    +0.053 |
| **Average**       |            0.729 |               0.761 |    +0.032 |

*(n=15 câu/config, tính trung bình cộng đơn giản trên 4 metric)*

## A/B comparison

- **Cấu hình tốt hơn: Hybrid + RRF** (trung bình 0.761 so với 0.729 của dense-only).
- **Evidence:** Hybrid thắng rõ ở *context recall* (+0.133) và *context precision* (+0.053) — BM25 bù được các câu hỏi có định danh cụ thể (số hiệu văn bản, tên riêng) mà dense một mình bỏ sót. Đổi lại, *faithfulness* giảm nhẹ (−0.047) vì một vài trường hợp BM25 đẩy nhầm 1 chunk không liên quan lên hạng cao qua RRF, khiến LLM có ít context đúng hơn để bám vào (xem "Worst performers"). *Answer relevance* gần như không đổi (−0.012, trong biên độ nhiễu) — hợp lý vì metric này chỉ đo độ khớp giữa câu hỏi và câu trả lời, không phụ thuộc trực tiếp retrieval method.
- **Trade-off về latency/cost:** Hybrid tốn thêm 1 lần gọi `lexical_search()` (BM25, chạy local trên CPU, không gọi API nên chi phí ~0) và 1 lần `rerank_rrf()` (thuần Python, O(n log n)) so với dense-only — chênh lệch latency không đáng kể (<50ms/câu, đo thủ công khi test). Không tốn thêm chi phí API vì BM25 và RRF đều chạy local.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | -------------- | ---------- |
|   1 | Nghị quyết 198/2025/QH15 định nghĩa hộ kinh doanh như thế nào? | hybrid | 1.00 | N/A (refusal) | 0.00 | N/A | retrieval | Câu hỏi vừa nêu số hiệu văn bản ("198/2025/QH15") vừa hỏi khái niệm. Cosine similarity giữa câu hỏi và chunk đúng chỉ 0.48 (văng khỏi top-30/1716), vì embedding bị kéo lệch về các chunk *nhắc tới số hiệu văn bản* thay vì chunk *chứa định nghĩa*. Test lại với câu đơn giản "Hộ kinh doanh là gì" → similarity 0.62, đúng chunk. BM25 cũng thất bại vì lý do ngược lại: token "198"/"QH15" hiếm (IDF cao) kéo chunk tiêu đề văn bản lên đầu, trong khi "hộ kinh doanh" quá phổ biến (IDF thấp) không đủ trọng số. |
|   2 | Theo Luật Thương mại điện tử 122/2025/QH15, nền tảng thương mại điện tử bao gồm những loại nào? | dense | 1.00 | N/A (refusal) | 0.00 | N/A | retrieval (near-miss) | Chunk đúng (`luat-122...::chunk-3`) xếp hạng **6/1716** (similarity 0.58) — ngay sát ngưỡng `top_k=5`, bị văng ra chỉ vì thiếu 1 bậc. Khác với case #1 (embedding sai hẳn hướng), đây là near-miss do `top_k` quá nhỏ khi nhiều chunk lân cận (Điều 2, Điều 27...) cùng cạnh tranh top-5 vì đều nói về "thương mại điện tử" ở mức tổng quát. |
|   3 | Theo khoản 5 Điều 17 Nghị định 68/2026, cơ quan thuế chỉ truy thu thuế các năm trước của hộ kinh doanh trong trường hợp nào? | hybrid | 0.50 | N/A | 0.00 | 0.92 | data quality | 2/5 chunk retrieve được từ `article_05.md` chỉ là **caption ảnh và link điều hướng** ("![Hộ kinh doanh... - Ảnh 2.]...", "* […]…") do crawl thô chưa lọc bỏ boilerplate của trang báo. Chunk mang câu trả lời đúng ("chỉ truy thu khi có cơ sở khẳng định... khai thuế sai") không lọt vào top-5, khiến LLM chỉ thấy nửa quy tắc (không dùng doanh thu 2026 để truy thu) mà thiếu vế ngoại lệ, trả lời không đầy đủ dù faithfulness với context nó thấy được là trung bình. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------- | ---------------- | -------------- |
|        1 | Lọc bỏ boilerplate (caption ảnh, menu, link chia sẻ) khỏi markdown tin tức trước khi chunk, ở `task3_convert_markdown.py::convert_news_articles()` | Case #3: 2/5 slot retrieval bị chunk rác caption ảnh chiếm chỗ | Tăng context recall/precision cho các câu hỏi liên quan tin tức (hiện thấp nhất trong 4 metric ở cả 2 config) | Re-run `run_eval.py`, so `context_precision`/`context_recall` trước/sau trên cùng 15 câu |
|        2 | Tăng `top_k` truy hồi trước khi RRF (hiện `retrieve()` đã lấy `top_k*2` trước fuse) lên `top_k*3-4` cho riêng dense, giảm rủi ro near-miss như case #2 | Case #2: chunk đúng xếp hạng 6, chỉ thiếu 1 bậc so với top_k=5*2=10 (thực ra top_k*2=10 đã đủ chứa rank 6 — nhưng generate_with_citation dùng top_k=5 mặc định cho câu trả lời cuối, nên chunk rank 6 vẫn bị cắt ở bước cuối) | Giảm tỷ lệ safe-refusal oan cho câu hỏi có nhiều chunk liên quan cạnh tranh | So sánh context_recall khi `top_k=5` vs `top_k=8` trên riêng 3 câu worst performers |
|        3 | Rewrite/chuẩn hoá câu hỏi trước khi embed: tách số hiệu văn bản ra khỏi phần ngữ nghĩa (ví dụ bằng regex nhận diện `NĐ|NQ|Luật số \d+/\d+`) rồi embed riêng phần khái niệm, kết hợp lại lúc fuse | Case #1: câu hỏi thuần khái niệm cho similarity đúng 0.62, câu có kèm số hiệu chỉ 0.48 | Cải thiện context recall cho nhóm câu hỏi "định danh + khái niệm" — nhóm lỗi nặng nhất hiện tại | Test A/B: query gốc vs query đã tách, đo lại context_recall trên case #1 |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | ------------: | -------------------: | ---------- |
| Chưa thực hiện | — | — | — | Nhóm chưa làm HyDE/query expansion, reranker nâng cao, hay conversation memory (mục bonus, không bắt buộc). Ưu tiên 3 khuyến nghị ở trên trước vì tác động trực tiếp tới 3 worst performer đã đo được. |
