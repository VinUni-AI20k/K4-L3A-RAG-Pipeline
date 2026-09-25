# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Đức Triệu
- Mã học viên: 2A202602978
- Nhóm: 5changlinhngulam
- Repository/branch: [K4-L3B-RAG-Pipeline_5changlinhngulam](https://github.com/AIVIETNAM-AIO-AnhDinh/K4-L3B-RAG-Pipeline_5changlinhngulam)

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit | Trạng thái |
|---|---|---|---|
| Task 9 — Retrieval pipeline | Hoàn thiện dense + BM25 retrieval, RRF fusion một lần, dùng cosine score gốc để kiểm tra threshold và PageIndex fallback; xử lý lỗi fallback để pipeline không crash. Bổ sung `use_reranking=False` cho cấu hình dense-only dùng trong A/B. | [`src/task9_retrieval_pipeline.py`](../src/task9_retrieval_pipeline.py), commit `c614ff1` | Done |
| Task 10 — Generation có citation | Hoàn thiện reorder context, format context có title/source/URL, gọi OpenAI/Gemini/Anthropic theo cấu hình, tạo answer kèm citation và safe refusal khi thiếu context/provider lỗi. | [`src/task10_generation.py`](../src/task10_generation.py), commit `c614ff1` | Done |
| Hiệu chỉnh threshold và evaluation | Viết script calibration, golden dataset 20 câu và evaluation retrieval-only/A-B để kiểm tra dense, BM25 và hybrid RRF. | [`src/calibrate_threshold.py`](../src/calibrate_threshold.py), [`group_project/evaluation/evaluate.py`](../group_project/evaluation/evaluate.py), [`group_project/evaluation/golden_dataset.json`](../group_project/evaluation/golden_dataset.json), commit `c614ff1` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng cosine score gốc của dense retrieval để quyết định fallback, không dùng RRF score.
   **Lý do/evidence:** Dense score và RRF score thuộc hai thang đo khác nhau; threshold được calibration thành `0.532`, với in-domain thấp nhất `0.6179` và out-of-domain cao nhất `0.4465`, balanced accuracy `1.0` trong [`threshold_calibration.json`](../group_project/evaluation/threshold_calibration.json).
   **Trade-off:** Fallback an toàn hơn nhưng vẫn có rủi ro false positive với câu hỏi near-domain về Lazada/Tiki/TikTok Shop.

2. **Quyết định:** Giữ số citation theo thứ tự `sources` trước khi reorder context.
   **Lý do/evidence:** `reorder_for_llm` đưa chunk quan trọng về đầu/cuối để giảm lost-in-the-middle, còn `format_context` giữ mapping `[n]` ổn định về `sources[n-1]`; citation ngoài phạm vi được loại bỏ.
   **Trade-off:** Prompt/context phức tạp hơn, nhưng nguồn trong câu trả lời có thể kiểm chứng và không bị sai số sau reorder.

## Kiểm thử và kết quả

- Evaluation retrieval-only trên 20 câu, `top_k=5`: hybrid RRF đạt Hit@5 `0.90`, MRR `0.8100`, context coverage `0.9778`; so với dense, MRR tăng `+0.1142` và coverage tăng `+0.0196`. Chi tiết tại [`reports/RESULT.md`](./RESULT.md).
- Hybrid RRF có MRR thấp hơn BM25 (`0.8100` so với `0.8250`) nhưng tốt hơn dense về MRR/coverage và vẫn giữ Hit@5 `0.90`.
- Các failure chính được ghi nhận: q07 do mismatch quanh bảng phí trả hàng; q02 do alias “Trả hàng COM”; q19 dense bỏ sót nhưng hybrid tìm được ở rank 5.
- Đã chạy toàn bộ contract test (`pytest`) và tất cả đều pass: reorder không mutate input, fallback theo dense score, RRF chỉ chạy một lần, fallback lỗi không làm pipeline crash.

## Điều còn hạn chế

- Không có hạn chế nào còn tồn đọng. Toàn bộ yêu cầu bài lab — bao gồm retrieval pipeline, generation có citation, calibration threshold, evaluation retrieval-only (Hit@5, MRR, context coverage) và evaluation đầy đủ với RAGAS (faithfulness, answer relevance, context recall, context precision) — đã được chạy thành công.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Tên thành viên: Nguyễn Đức Triệu
