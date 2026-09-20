# RAG evaluation results

## Run information

| Field | Value |
| --- | --- |
| Evaluation date | 2026-09-20 |
| Framework and version | RAGAS 0.4.3 (declared dependency); acceptance validation with pytest |
| Evaluator model | Not configured; no model-based scoring was run |
| Generator model | Configurable through `LLM_PROVIDER`; not invoked in this validation |
| Embedding model | Project default from the semantic-search module |
| Corpus version/commit | Current working tree, traffic-law corpus |
| Golden dataset size | 15 grounded cases |
| `top_k` | 5 recommended for the benchmark |
| Fallback threshold and calibration | Project default; calibration still requires an end-to-end model run |

## Configurations

- **Config A — dense-only:** semantic retrieval using the shared embedding model and vector collection.
- **Config B — hybrid + RRF:** dense retrieval combined with BM25 and reciprocal-rank fusion.

Both configurations must use the same golden dataset, generator, evaluator, prompt and `top_k`; only the retrieval strategy changes.

## Overall scores

Model-based evaluation was not executed because no evaluator credentials or fixed evaluator model were configured. Reporting invented scores would make the comparison irreproducible.

| Metric | Config A | Config B | Delta B−A |
| --- | ---: | ---: | ---: |
| Faithfulness | N/A | N/A | N/A |
| Answer relevance | N/A | N/A | N/A |
| Context recall | N/A | N/A | N/A |
| Context precision | N/A | N/A | N/A |
| **Average** | N/A | N/A | N/A |

## A/B comparison

- Better configuration: not determined without a controlled evaluator run.
- Evidence: the repository now contains 15 grounded cases and both retrieval contracts, but no persisted per-case metric output.
- Latency/cost trade-off: hybrid retrieval performs both dense and lexical searches plus fusion, so it is expected to cost more retrieval time than dense-only; this must be measured in the same run as quality.

## Worst performers

No numeric ranking is claimed before evaluation. The following cases are the highest-risk cases identified from corpus inspection and should be reviewed first.

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Thời gian thực hành của từng hạng B/C1 là bao nhiêu? | Both | N/A | N/A | N/A | N/A | retrieval/data | Answer depends on preserving a multi-column table correctly. |
| 2 | Xe từ bao nhiêu chỗ phải lắp camera khoang khách? | Both | N/A | N/A | N/A | N/A | retrieval | Exact numeric threshold may be separated from its legal condition during chunking. |
| 3 | Nghị định 236/2026/NĐ-CP sửa đổi văn bản nào? | Both | N/A | N/A | N/A | N/A | retrieval | Several similar decree numbers occur in nearby context. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| ---: | --- | --- | --- | --- |
| 1 | Run both configurations with one fixed evaluator model and persist per-case output. | Current report has no reproducible numeric measurements. | Produces a defensible A/B conclusion. | Save all four metrics, latency and retrieved chunk IDs for every golden case. |
| 2 | Preserve Markdown tables and headings during chunking. | Training-hour questions depend on table structure. | Improves context recall and numeric accuracy. | Re-run table questions and inspect retrieved chunks. |
| 3 | OCR the four image-only legal PDFs. | Their standardized records currently contain metadata only. | Expands authoritative legal coverage. | Confirm extracted text, then add legal-document cases to the golden set. |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| --- | --- | ---: | ---: | --- |
| No bonus experiment run | Dense-only versus hybrid + RRF | N/A | N/A | Establish the reproducible baseline before adding query expansion or advanced reranking. |
