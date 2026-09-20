# RAG evaluation results — IELTS Writing

## Run information

| Field | Value |
| --- | --- |
| Evaluation date | 2026-09-20 |
| Framework and version | Ragas 0.4.3 |
| Evaluator model | OpenAI `gpt-4.1-mini`; answer relevance uses `text-embedding-3-small` |
| Generator model | OpenAI `gpt-4.1-mini`, temperature 0.3, top_p 0.9 |
| Embedding model | `BAAI/bge-m3` via sentence-transformers |
| Corpus version/commit | 15 local standardized IELTS documents, 979 indexed chunks; code at `12d0ac1`. Corpus files are not yet committed. |
| Golden dataset size | 15 source-grounded questions in `golden_dataset.json` |
| `top_k` | 5 for both configurations |
| Fallback threshold and calibration | Production default 0.5. On six in-domain questions, top dense cosine: min 0.5907, mean 0.6895. On five out-of-domain questions: max 0.6529, mean 0.4847. Scores overlap, so threshold 0.5 is provisional. PageIndex was disabled in the A/B comparison to isolate retrieval strategy. |

## Configurations

- **Config A — dense-only:** top 5 Chroma cosine results from `semantic_search`.
- **Config B — hybrid + RRF:** dense and BM25 candidates, fused once by `rerank_rrf`, top 5 results. Fallback disabled for the comparison.

Both configurations used the same golden questions, generation prompt, generator, evaluator, embedding model, and `top_k`. The command `python -m group_project.evaluation.run_evaluation --generate` saved each answer and its retrieved chunks locally; `--score` scored those saved answers with Ragas. The local `run_results.json` is excluded from Git because it contains full retrieved excerpts.

## Overall scores

Mean over the same 15 questions; higher is better. These are LLM-judged scores, not human ratings.

| Metric | Config A | Config B | Delta B−A |
| --- | ---: | ---: | ---: |
| Faithfulness | 0.8333 | 0.9000 | +0.0667 |
| Answer relevance | 0.8076 | 0.8817 | +0.0742 |
| Context recall | 0.8667 | 0.8667 | 0.0000 |
| Context precision | 0.6500 | 0.6676 | +0.0176 |
| **Average** | **0.7894** | **0.8290** | **+0.0396** |

## A/B comparison

Hybrid + RRF scored higher on three of four metrics and tied on context recall. Dense returned a safe refusal on two questions; hybrid did so on one. The exact document named in the golden case appeared in the top five for 11/15 dense queries and 12/15 hybrid queries. This source-hit count is stricter than answer correctness because other documents can support the same fact.

Observed mean retrieval-plus-generation latency was 2.265 s for dense and 1.593 s for hybrid. The first dense query included local model loading (11.4 s). Excluding that cold start, dense averaged 1.613 s versus 1.593 s for hybrid; this small difference does not establish a speed advantage. The same model and top five context limit were used, but token-level API cost was not recorded.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Band 7 Lexical Resource in Task 2 | A and B | 0.00 | 0.00 | 0.00 | 0.00 | retrieval | Top chunks included Band 1 and generic criteria, but omitted the Band 7 Lexical Resource description; both configurations refused. |
| 2 | Band 6 Grammatical Range and Accuracy in Task 2 | A | 0.00 | 0.00 | 0.00 | 0.00 | retrieval | Top chunks covered Band 1 and Band 7, not the requested Band 6; the answer was a safe refusal. |
| 3 | Band 6 Grammatical Range and Accuracy in Task 2 | B | 1.00 | 1.00 | 0.00 | 0.00 | retrieval/generation | The answer cited a chunk containing Band 7 wording as if it described Band 6. Faithfulness was high because the answer matched that wrong chunk; reference-based recall and precision exposed the band mismatch. |
| 4 | Academic Writing Task 1 activity | A and B | 1.00 | 0.78 / 0.85 | 1.00 | 0.20 | retrieval | Both configurations returned several adjacent sample-task and criteria chunks; only one was useful for the short question. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| ---: | --- | --- | --- | --- |
| 1 | Prefix each band-descriptor chunk with its Task number, band, and criterion heading, then re-index. | Band 7 Lexical Resource and Band 6 Grammar queries retrieved Band 1/Band 7 chunks without enough heading context. | Reduce band confusion and unsupported refusals. | Re-run golden cases 11 and 12; inspect retrieved IDs and reference-based recall. |
| 2 | Tune retrieval for specific task/band terms and reduce redundant chunks from the same document. | Academic Task 1 context precision was 0.20 in both runs; exact source hit rose only from 11 to 12. | Improve context precision while retaining recall. | Re-run all 15 cases with the same generator and evaluator. |
| 3 | Add an answer check for requested band and task labels before presenting a cited answer. | Hybrid's Band 6 Grammar answer repeated Band 7 evidence with a valid citation. | Catch answers that are faithful to a wrong section. | Test a Band 6 query against a retrieved Band 7 chunk and require refusal or correction. |

## Demo

- In-domain: “What is the minimum word count for IELTS Writing Task 2?” returned “250 words or more” with three citations pointing to retrieved chunks.
- Out-of-domain: “How do I cook Vietnamese pho at home?” returned the safe refusal with no sources.

## Bonus experiments

No bonus experiment was run. The A/B comparison above is the required dense-versus-hybrid evaluation.

## Limits

The corpus and Chroma index are currently local. The score estimates come from 15 questions and one evaluator model; a human review of cited facts, particularly band descriptors, is still needed. PageIndex had no API key during this run, so its fallback quality was not measured.
