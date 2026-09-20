# RAG evaluation results

## Run information

| Field | Value |
| --- | --- |
| Evaluation date | 2026-09-20 (Asia/Bangkok) |
| Framework | Custom reproducible evaluator v1; deterministic token-overlap/F1 proxies in `run_evaluation.py` |
| Evaluator | No external judge; metrics are deterministic proxies computed from golden answer/context |
| Generator | FPT AI Factory `DeepSeek-V4-Flash`; temperature 0.3; top-p 0.9; max output 4096 |
| Embedding | `BAAI/bge-m3` through sentence-transformers |
| Corpus version | Commit `9371c76`; 9 standardized documents; 665 chunks |
| Golden dataset | 18 fixed cases |
| `top_k` | 5 for both configurations; hybrid retrieves 10 candidates per method before fusion |
| Fallback calibration | `0.50`; three in-domain scores: 0.7266, 0.7514, 0.7014; three out-of-domain scores: 0.3705, 0.4327, 0.3653 |

The A/B runner bypasses fallback in both configurations. Golden dataset, corpus, generator, prompt, evaluator and `top_k` are identical; only retrieval changes.

## Configurations

- **Config A — dense-only:** BGE-M3 query embedding → Chroma cosine search → top 5.
- **Config B — hybrid + RRF:** the same dense search and BM25 each return 10 candidates → one RRF call (`k=60`) → top 5.

## Overall scores

| Metric | Config A | Config B | Delta B−A |
| --- | ---: | ---: | ---: |
| Faithfulness | 0.8721 | 0.9100 | +0.0379 |
| Answer relevance | 0.5660 | 0.6073 | +0.0413 |
| Context recall | 0.9762 | 0.9734 | -0.0028 |
| Context precision | 0.8111 | 0.8222 | +0.0111 |
| **Average** | **0.8064** | **0.8282** | **+0.0219** |
| Mean end-to-end latency | 10.207 s | 5.056 s | -5.151 s (-50.5%) |

## A/B comparison

Config B is the recommended default. It improves faithfulness, answer relevance and context precision, raising the four-metric average by 0.0219. Context recall decreases slightly by 0.0028, so hybrid is better overall but not uniformly better. Both configurations make 18 generation calls; BM25 and RRF run locally and add no provider call. The observed latency difference is treated as provider/runtime variance because each configuration was run only once and token usage was not recorded.

## Worst performers and root cause

| # | Question/config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Case 12, A and B: thời gian/trình tự trở lại học kỳ 1 | 0.0000 | 0.0000 | 0.5714 | 1.0000 | retrieval/chunking | Both paths retrieve the notice heading and surrounding registration notices but miss the adjacent chunk containing `05/05/2026–15/08/2026` and the instruction “đăng ký lớp, không đăng ký học phần”. Safe refusal is correct. |
| 2 | Case 4, A: hạn đăng ký học phần kỳ 1 | 0.5714 | 0.2000 | 1.0000 | 0.8000 | retrieval/generation | Dense retrieves the correct `27/4/2026` chunk together with an older/different `19/4/2026` summer-registration chunk. The answer contains the correct date but adds an unnecessary conflict caveat, reducing relevance and faithfulness. Hybrid ranks the cleaner evidence and performs better. |
| 3 | Case 13, A: tiên quyết/học trước/song hành | 0.7317 | 0.5333 | 1.0000 | 0.6000 | chunking/evaluator | The definition crosses chunks 49–50. Retrieval contains the evidence and the generated answer is substantively correct, but extra wording and the lexical proxy penalize paraphrases. This is partly a chunk-boundary issue and partly a metric limitation. |

## Recommendations

| Priority | Action | Expected impact | Verification |
| ---: | --- | --- | --- |
| 1 | Add adjacent-chunk expansion after retrieval without a second RRF call. | Recover the decisive procedure/date for case 12. | Rerun the same 18 cases; case 12 must answer correctly while precision decreases by no more than 0.02. |
| 2 | Deduplicate or annotate superseded/conflicting schedule passages by semester and publication date. | Reduce false conflicts such as case 4. | Confirm the final context contains the correct semester-specific date and rerun case 4. |
| 3 | Compare sentence/heading-aware chunking against the fixed 500/50 baseline. | Keep related definitions together for case 13. | Re-index and rerun the unchanged golden set; require no recall regression. |
| 4 | Repeat each config at least three times and record prompt/completion tokens. | Make latency and cost comparison defensible. | Report mean, p50/p95 and token totals per configuration. |

## Reproduction

```powershell
python -m src.task4_chunking_indexing
python -m group_project.evaluation.run_evaluation
pytest tests/test_acceptance.py -q
```

Raw case-level answers, context IDs, metrics and latency are stored in `evaluation_details.json`. No bonus reranker was evaluated.