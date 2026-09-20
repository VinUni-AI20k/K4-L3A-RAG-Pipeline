# RAG evaluation results

## Run information

| Field | Value |
| --- | --- |
| Evaluation date | 2026-09-20 |
| Framework and version | Custom deterministic Unicode-token evaluator (`src/task11_evaluation.py`) |
| Evaluator model | None; lexical overlap against grounded golden answers and contexts |
| Generator model | OpenAI `gpt-4o-mini` |
| Embedding model | OpenAI `text-embedding-3-small` |
| Corpus version/commit | 8 standardized documents, 1,578 indexed chunks |
| Golden dataset size | 15 |
| `top_k` | 5 |
| Fallback threshold and calibration | `0.62`; calibrated with in-domain and out-of-domain queries |

The evaluation uses four deterministic signals: faithfulness, answer
relevance, context recall and context precision. Both configurations use the
same questions, generator, prompt and `top_k`.

## Configurations

- **Config A — dense-only:** top-5 Chroma cosine retrieval using `text-embedding-3-small`.
- **Config B — hybrid + RRF:** top-10 dense plus top-10 BM25L, fused once with RRF (`k=60`), then top 5.

## Overall scores

| Metric | Config A | Config B | Delta B−A |
| --- | ---: | ---: | ---: |
| Faithfulness | 0.8839 | 0.9049 | +0.0210 |
| Answer relevance | 0.7266 | 0.7107 | -0.0159 |
| Context recall | 0.9889 | 1.0000 | +0.0111 |
| Context precision | 0.7467 | 0.7467 | +0.0000 |
| **Average** | **0.8365** | **0.8406** | **+0.0041** |

## A/B comparison

- **Cấu hình tốt hơn:** Config B — hybrid + RRF.
- **Evidence:** faithfulness tăng 0.0210, context recall đạt 1.0000 và average tăng 0.0041.
- **Trade-off:** hybrid có thêm BM25L/RRF nhưng không thêm lượt gọi LLM; dense-only đơn giản và nhanh hơn.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Thuật ngữ nhiệt động học có hai nghĩa nào? | hybrid + RRF | 0.9545 | 0.6286 | 1.0000 | 0.2000 | retrieval | RRF giữ nhiều chunk liên quan yếu với bài viết ngắn. |
| 2 | Vectơ cường độ điện trường trên đường sức có phương và chiều thế nào? | dense-only | 0.7273 | 0.5000 | 0.8333 | 0.8000 | generation | OCR và cách diễn đạt vector làm giảm trùng khớp token. |
| 3 | Bước sóng được xác định bằng khoảng cách giữa những phần tử nào? | hybrid + RRF | 0.8400 | 0.6222 | 1.0000 | 0.4000 | retrieval | BM25 bổ sung chunk liên quan yếu cạnh đoạn chính. |

## Recommendations

| Priority | Action | Expected impact | How to verify |
| ---: | --- | --- | --- |
| 1 | Làm sạch OCR công thức, dấu tiếng Việt và thuật ngữ vector. | Tăng relevance và grounding. | Đối chiếu lại PDF gốc và đánh giá lại. |
| 2 | Lọc chunk liên quan yếu trước RRF với câu hỏi ngắn. | Tăng context precision. | So sánh precision trên cùng golden dataset. |
| 3 | Bổ sung query ngoài domain để hiệu chỉnh threshold. | Giảm fallback nhầm hoặc bỏ sót. | Lập confusion matrix với ít nhất 10 query mới. |

## Bonus experiment

| Experiment | Baseline | Metric delta | Conclusion |
| --- | --- | ---: | --- |
| Dense-only vs hybrid + RRF | Dense-only average 0.8365 | +0.0041 average | Hybrid được chọn vì faithfulness và recall tốt hơn. |
