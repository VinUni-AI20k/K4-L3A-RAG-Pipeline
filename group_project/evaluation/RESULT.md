# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | Custom deterministic Unicode-token evaluator; results recorded in `evaluation_runs.json` |
| Evaluator model                    | None; lexical overlap against the grounded golden answers/contexts |
| Generator model                    | OpenAI `o4-mini` |
| Embedding model                    | `BAAI/bge-m3` |
| Corpus version/commit              | Working tree, 8 standardized documents, 1,578 indexed chunks |
| Golden dataset size                | 15 |
| `top_k`                            | 5 |
| Fallback threshold and calibration | `0.62`; golden top-1 dense scores 0.632–0.803, out-of-domain probes 0.413–0.607 |

The evaluator is intentionally deterministic and rerunnable without evaluator
LLM calls. Faithfulness is the fraction of answer tokens found in retrieved
context; answer relevance is token F1 against `expected_answer`; context recall
is expected-context token recall; context precision is the fraction of retrieved
chunks with substantial expected-context overlap. The same `o4-mini` prompt and
the same 15 questions were used for both configurations.

## Configurations

- **Config A — dense-only:** top-5 Chroma cosine retrieval from `BAAI/bge-m3`.
- **Config B — hybrid + RRF:** top-10 dense + top-10 BM25L, fused once with RRF (`k=60`), then top 5.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      | 0.8839 | 0.9049 | +0.0210 |
| Answer relevance  | 0.7266 | 0.7107 | -0.0159 |
| Context recall    | 0.9889 | 1.0000 | +0.0111 |
| Context precision | 0.7467 | 0.7467 | +0.0000 |
| **Average**       | **0.8365** | **0.8406** | **+0.0041** |

## A/B comparison

- Cấu hình tốt hơn: **Config B — hybrid + RRF**, theo average score (+0.0041).
- Evidence: hybrid tăng faithfulness từ 0.8839 lên 0.9049 và đạt context recall 1.0; answer relevance giảm nhẹ 0.0159.
- Trade-off về latency/cost: hybrid chạy thêm BM25 và RRF nhưng không gọi thêm LLM; generation vẫn dùng cùng một model và prompt. Dense-only đơn giản và nhanh hơn, hybrid giữ bằng chứng đầy đủ hơn.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ---------------- | ---------- |
| 1 | Theo bài viết, thuật ngữ nhiệt động học có hai nghĩa nào? | hybrid + RRF | 0.9545 | 0.6286 | 1.0000 | 0.2000 | retrieval | RRF giữ nhiều chunk liên quan yếu cạnh đoạn bài viết ngắn |
| 2 | Vectơ cường độ điện trường tại một điểm trên đường sức điện có phương và chiều như thế nào? | dense-only | 0.7273 | 0.5000 | 0.8333 | 0.8000 | generation | OCR và cách diễn đạt vector làm giảm trùng token với đáp án chuẩn |
| 3 | Bước sóng được xác định bằng khoảng cách giữa những phần tử môi trường nào? | hybrid + RRF | 0.8400 | 0.6222 | 1.0000 | 0.4000 | retrieval | BM25 bổ sung chunk công thức/khái niệm nhưng làm giảm tỷ lệ chunk trực tiếp liên quan |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
| 1 | Làm sạch OCR cho công thức, dấu tiếng Việt và thuật ngữ vector | Dense article_03 có recall 0.8333 và relevance 0.5 | Tăng answer relevance và giảm lỗi grounding | OCR QA lại các trang tương ứng rồi chạy lại evaluator |
| 2 | Thử lọc chunk theo source/page trước RRF khi câu hỏi rất ngắn | article_04 hybrid precision chỉ 0.2 | Tăng context precision mà không đổi generator | So sánh precision trên cùng 15 câu |
| 3 | Calibrate threshold bằng nhiều query ngoài domain hơn | Khoảng dense score phụ cận 0.543–0.607 gần ngưỡng 0.62 | Giảm fallback nhầm hoặc bỏ sót | Thêm tối thiểu 10 query ngoài domain và ghi confusion matrix |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Dense-only vs hybrid + RRF | Dense-only average 0.8365 | +0.0041 average | Hybrid thêm BM25/RRF, không thêm LLM call | Hybrid được chọn vì recall/faithfulness tốt hơn, dù relevance giảm nhẹ |
