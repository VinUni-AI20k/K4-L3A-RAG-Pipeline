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

The evaluator reports four deterministic signals. Faithfulness is the fraction
of answer tokens found in retrieved context; answer relevance is token F1
against `expected_answer`; context recall is expected-context token recall; and
context precision is the fraction of retrieved chunks with substantial overlap
with the expected context. Both configurations use the same questions,
generator, prompt and `top_k`.

## Configurations

- **Config A — dense-only:** top-5 Chroma cosine retrieval using `text-embedding-3-small`.
- **Config B — hybrid + RRF:** top-10 dense results plus top-10 BM25L results, fused once with RRF (`k=60`), then truncated to top 5.

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
- **Evidence:** hybrid tăng faithfulness từ 0.8839 lên 0.9049 và context recall lên 1.0000; average tăng 0.0041.
- **Trade-off:** hybrid cần thêm BM25L và bước RRF nhưng không phát sinh thêm lượt gọi LLM. Dense-only đơn giản hơn, còn hybrid giữ bằng chứng đầy đủ hơn.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Theo bài viết, thuật ngữ nhiệt động học có hai nghĩa nào? | hybrid + RRF | 0.9545 | 0.6286 | 1.0000 | 0.2000 | retrieval | RRF giữ nhiều chunk liên quan yếu bên cạnh đoạn bài viết ngắn. |
| 2 | Vectơ cường độ điện trường tại một điểm trên đường sức điện có phương và chiều như thế nào? | dense-only | 0.7273 | 0.5000 | 0.8333 | 0.8000 | generation | OCR và cách diễn đạt vector làm giảm mức trùng khớp với đáp án chuẩn. |
| 3 | Bước sóng được xác định bằng khoảng cách giữa những phần tử môi trường nào? | hybrid + RRF | 0.8400 | 0.6222 | 1.0000 | 0.4000 | retrieval | BM25 bổ sung chunk công thức/khái niệm nhưng làm giảm tỷ lệ chunk trực tiếp liên quan. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| ---: | --- | --- | --- | --- |
| 1 | Làm sạch OCR cho công thức, dấu tiếng Việt và thuật ngữ vector. | Bài viết về điện trường có recall 0.8333 và relevance 0.5. | Tăng answer relevance và giảm lỗi grounding. | Kiểm tra lại các trang OCR liên quan và đối chiếu PDF gốc. |
| 2 | Lọc hoặc giảm trọng số chunk liên quan yếu trước RRF với câu hỏi rất ngắn. | Bài viết về nhiệt động học có context precision 0.2. | Tăng context precision mà không đổi generator. | So sánh precision trên cùng 15 câu hỏi. |
| 3 | Bổ sung query ngoài domain để hiệu chỉnh threshold. | Một số dense score ngoài domain nằm gần ngưỡng 0.62. | Giảm fallback nhầm hoặc bỏ sót bằng chứng. | Bổ sung ít nhất 10 query và lập confusion matrix. |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| --- | --- | ---: | --- | --- |
| Dense-only vs hybrid + RRF | Dense-only average 0.8365 | +0.0041 average | Hybrid thêm BM25L/RRF, không thêm lượt gọi LLM | Chọn hybrid vì faithfulness và recall tốt hơn. |
