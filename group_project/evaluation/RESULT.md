# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | ragas 0.4.3 (API `ragas.metrics.collections`), script `src/task11_evaluation.py` |
| Evaluator model                    | OpenAI `gpt-4o-mini` (judge) + `text-embedding-3-small` (cho answer relevancy) |
| Generator model                    | OpenAI `gpt-4o-mini`, temperature 0.3, top_p 0.9, prompt trong `src/task10_generation.py` |
| Embedding model                    | `BAAI/bge-m3` (sentence-transformers, CPU), ChromaDB cosine, 985 chunks |
| Corpus version/commit              | `0fb3190` (5 PDF legal + 10 bài news, chuẩn hoá Markdown) |
| Golden dataset size                | 20 câu (`golden_dataset.json`), 12 tiếng Anh + 8 tiếng Việt, 6 nhóm: criteria, requirements, scoring, band_descriptor (8 câu), task_format, advice |
| `top_k`                            | 5 (RRF lấy 10 ứng viên mỗi nhánh rồi cắt còn 5) |
| Fallback threshold and calibration | Cosine dense top-1 ≥ 0.53 thì dùng hybrid, dưới thì thử PageIndex. Hiệu chỉnh bằng 6 query in-domain (min 0.5907) và 6 query out-of-domain (max 0.4714), chọn giữa khoảng trống. Trong run này **0/20** câu golden rơi xuống fallback (dense top-1 thấp nhất 0.631). |

Số liệu chi tiết từng câu, context đã lấy, latency và câu trả lời nằm trong `results/config_A.json`, `results/config_B.json`, tổng hợp ở `results/summary.md`. Chạy lại bằng `python -m src.task11_evaluation`.

## Configurations

- **Config A — dense-only:** `semantic_search(query, top_k=10)` bằng bge-m3 trên ChromaDB, cắt còn 5 chunk đầu theo cosine; không chạy BM25, không RRF (`retrieve_detailed(..., use_reranking=False)`).
- **Config B — hybrid + RRF:** `semantic_search` + `lexical_search` (BM25Okapi trên cùng 985 chunk), mỗi nhánh 10 ứng viên, gộp bằng `rerank_rrf` (k=60) đúng một lần, lấy 5 chunk đầu (`use_reranking=True`). Đây là cấu hình mặc định của chatbot.

Hai config phải dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy. Cả hai đi qua cùng ngưỡng fallback và cùng bước reorder + citation check trong `generate_from_chunks`.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      |   0.6833 |   0.7000 |   +0.0167 |
| Answer relevance  |   0.6128 |   0.5802 |   −0.0326 |
| Context recall    |   0.7881 |   0.8476 |   +0.0595 |
| Context precision |   0.7767 |   0.6160 |   −0.1607 |
| **Average**       |   0.7152 |   0.6860 |   −0.0292 |

Ghi chú cách đọc: safe refusal được chấm faithfulness = 0 và relevance = 0 (câu trả lời không chứa nội dung), nên hai metric này bị kéo xuống trực tiếp bởi số câu refusal: A 5/20, B 6/20. Nếu chỉ tính 14 câu cả hai config đều trả lời, faithfulness A = 0.905, B = 1.000; precision A = 0.931, B = 0.747.

## A/B comparison

- Cấu hình tốt hơn: **Không có cấu hình thắng tuyệt đối; nhóm giữ Config B (hybrid + RRF) cho sản phẩm.** B tốt hơn ở hai metric phản ánh "có lấy được đúng bằng chứng và trả lời bám bằng chứng không" (recall +0.06, faithfulness +0.02), A tốt hơn ở precision (+0.16) và relevance (+0.03). Với n = 20 và judge LLM có nhiễu (ví dụ g01/A bị chấm faithfulness 0.0 dù câu trả lời đúng và có citation), chênh lệch trung bình 0.03 không đủ để kết luận A hơn B.
- Evidence:
  - Recall: B kéo được chunk đúng vào top-5 ở g06 (0.67 → 1.00), g15 (0.00 → 0.75), g07 (0.00 → 0.75), g10 (0.25 → 0.75) nhờ BM25 khớp từ khoá "Task Response", "Band 7", "Grammatical Range".
  - Precision: B giảm ở 13/20 câu, tăng ở 3 câu (g05 1.00 → 0.70, g08 1.00 → 0.50, g17 0.83 → 0.33). Nguyên nhân là BM25 đẩy vào các chunk chứa từ khoá phổ biến ("Band", "Task 2", "Writing") nhưng không trả lời câu hỏi, đặc biệt các chunk Band 1 của band descriptor có câu boilerplate "Responses of 20 words or fewer" lặp ở mọi tiêu chí.
  - Refusal: 5 câu refusal chung của cả hai config (g07, g09, g10, g13, g16) đều là **retrieval miss** — chunk đúng không nằm trong top-5 nên LLM từ chối đúng theo prompt. B có thêm g18 là **generation miss** (context đã chứa câu trả lời, recall 1.0, nhưng LLM từ chối; chạy lại cùng input thì có lúc trả lời được).
- Trade-off về latency/cost: Retrieval median A = 116 ms, B = 113 ms (BM25 in-memory gần như không thêm chi phí; số 868 ms trung bình của A trong `summary.md` là do câu đầu tiên gánh 14.9 s load bge-m3, B chạy sau nên hưởng cache). Generation median ~1.3–1.4 s, bằng nhau vì cùng prompt và cùng số chunk. Chi phí evaluator ≈ 8 lời gọi judge/câu/config, tổng ~320 lời gọi gpt-4o-mini cho một lần chạy A+B.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------- | ---------- |
|   1 | g13 — Compare Lexical Resource at Band 8 and Band 9 for Writing Task 1 | B | 0.00 | 0.00 | 0.00 | 0.00 | retrieval | Top-5 toàn chunk Band 1 (`band-descriptors::chunk-31/32/62`) và bài "Band 9 sample answers". Chunking tách heading `## Writing Task 1 — Band 8` khỏi phần `### Lexical Resource` bên dưới, nên chunk chứa nội dung Band 8/9 không mang từ "Band 8"; cả dense lẫn BM25 không phân biệt được các band. |
|   2 | g16 — Can I use bullet points in my IELTS Writing answer? | A, B | 0.00 | 0.00 | 1.00 / 1.00 | 0.00 | retrieval | Chunk đúng nằm trong `legal/ielts-writing-key-assessment-criteria.md` (câu "using bullet points ... is not appropriate") nhưng top-5 là các chunk FAQ "Can I use contractions / idioms / personal pronouns?" của ieltsadvantage — retrieval ưu tiên chunk có dạng câu hỏi giống hệt hơn chunk chính sách chứa từ khoá. Recall 1.0 do judge chấm sai (context không có "bullet points"). |
|   3 | g18 — Điểm Writing tổng được tính như thế nào từ bốn tiêu chí? | B | 0.00 | 0.00 | 1.00 | 0.33 | generation | Context có đủ (`ieltstutors::chunk-2`, `ielts-writing::chunk-2` nói rõ trung bình 4 tiêu chí, Task 2 nặng gấp đôi) nhưng gpt-4o-mini với temperature 0.3 lúc trả lời, lúc từ chối; run trước đó cùng câu này trả lời nhưng viết citation thiếu tiền tố `news/` nên bị refusal giả — đã sửa parser (`normalize_citations`) ở run cuối. |

Các câu g07, g09, g10 (band descriptor, refusal ở cả hai config) có cùng root cause với #1.

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Chunking giữ heading context: khi tách `ielts-writing-band-descriptors.md`, prepend heading cha (`Writing Task 1 — Band 8`) vào mỗi chunk `### <criterion>` (hoặc chunk theo cặp band × criterion). | 4/6 refusal (g07, g09, g10, g13) là câu hỏi "Band N + tiêu chí" mà top-5 không có chunk đúng; chunk lấy được là Band 1 vì mọi chunk band đều thiếu số band. | Recall của nhóm band_descriptor (8 câu, hiện 0.77 ở B, 4/8 refusal) lên >0.9; refusal toàn bộ golden set 6 → ≤2. | Re-index, chạy `python -m src.task11_evaluation --config B`; so recall và refusal trên g07/g09/g10/g13. |
|        2 | Thêm reranker (bge-reranker hoặc Jina) sau RRF: lấy 10 ứng viên hybrid, rerank cross-encoder, cắt 5. | Precision B thấp hơn A 0.16 do BM25 đưa chunk khớp từ khoá nhưng không liên quan (g08, g17, g05); RRF chỉ gộp thứ hạng, không nhìn nội dung. | Precision B lên ngang A (~0.78) mà vẫn giữ recall của hybrid. | Chạy A/B thứ ba "hybrid + RRF + rerank" cùng golden set; precision tăng, recall không giảm. |
|        3 | Ổn định generation: temperature 0 cho generator và cho phép LLM trả lời khi context đủ nhưng citation lệch format (đã có `normalize_citations`); log câu trả lời thô trước khi refusal để phân loại refusal thật/giả. | g18 (B) refusal dù recall 1.0; cùng input chạy 6 lần thì 2 lần citation sai format, 1 lần refusal. | Loại bỏ refusal giả do generation; faithfulness B ≥ 0.75. | Chạy g18 và 5 câu refusal 5 lần mỗi câu, tỉ lệ refusal trên câu có context đúng phải = 0. |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Không thực hiện | — | — | — | Nhóm ưu tiên hoàn thiện pipeline bắt buộc và A/B; PageIndex fallback đã tích hợp nhưng không kích hoạt trên golden set (0/20) nên chưa đo được. |
