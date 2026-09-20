# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | RAGAS 0.4.3 / Python 3.13 |
| Evaluator model                    | Gemini 2.0 Flash |
| Generator model                    | Gemini 2.0 Flash |
| Embedding model                    | Gemini embedding-001 |
| Corpus version/commit              | Local corpus V?nh H? Long |
| Golden dataset size                | 18 |
| `top_k`                            | 5 |
| Fallback threshold and calibration | dense cosine 0.30, calibrated on in-domain and out-of-domain queries |

## Configurations

- **Config A ? dense-only:** dense retrieval, no BM25, no RRF, top_k=5.
- **Config B ? hybrid + RRF:** dense + BM25, RRF k=60, top_k=5.

Hai config d?ng c?ng golden dataset, generator, evaluator, prompt v? `top_k`; ch? thay retrieval strategy.

## Overall scores

| Metric            | Config A | Config B | Delta B?A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      |     0.82 |     0.86 |     +0.04 |
| Answer relevance  |     0.79 |     0.84 |     +0.05 |
| Context recall    |     0.74 |     0.81 |     +0.07 |
| Context precision |     0.77 |     0.83 |     +0.06 |
| **Average**       |     0.78 |    0.835 |    +0.055 |

## A/B comparison

- C?u h?nh t?t h?n: **Config B ? hybrid + RRF**
- Evidence: retrieval k?t h?p BM25 gi?p b?t ??ng c?c thu?t ng? ph?p l? nh? s? hi?u v?n b?n v? t?n ??a danh, trong khi dense b? sung ng? ngh?a.
- Trade-off v? latency/cost: hybrid th?c hi?n th?m BM25 v? RRF n?n latency t?ng nh?; v?i corpus hi?n t?i, chi ph? kh?ng ??ng k?.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage             | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------------------- | ---------- |
|   1 | S? hi?u v?n b?n ? query d?ng vi?t t?t | A      |         0.60 |      0.58 |   0.42 |      0.45 | retrieval | dense-only b? s?t exact match |
|   2 | H?i ng?y ban h?nh c?a v?n b?n ph?p l? | B      |         0.72 |      0.70 |   0.55 |      0.61 | retrieval | chunk b? chia c?t metadata |
|   3 | H?i tr?i nghi?m du kh?ch t?ng h?p | A      |         0.68 |      0.66 |   0.50 |      0.53 | generation | context ch?a b?i tin qu? ng?n |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Gi? nguy?n s? hi?u/ph?p l? trong chunk v? t?ng BM25 | Worst case 1 | T?ng context recall | Ch?y queries s? hi?u tr?n A/B |
|        2 | T?ng chunk overlap quanh metadata | Worst case 2 | Tr?nh m?t ng?y/ng??i k? | Ki?m tra chunk ??u m?i v?n b?n |
|        3 | L?m s?ch heading v? c?t navigation ? b?n news | Worst case 3 | Gi?m nhi?u context | So s?nh ?? d?i h?u ?ch tr??c/sau normalize |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Conversation memory | Ch?a c? | Ch?a ?o | nh? | Ch?a ??t m?c ti?u lab |
| UI source highlighting | Hi?n th? text thu?n | N/A | kh?ng ??ng k? | H?u ?ch, c?n t?ch h?p citation link |
