# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | ragas 0.4.3 (API `ragas.metrics.collections`), script `src/task11_evaluation.py` |
| Evaluator model                    | OpenAI `gpt-4o-mini` (judge) + `text-embedding-3-small` (cho answer relevancy) |
| Generator model                    | OpenAI `gpt-4o-mini`, temperature 0.3, top_p 0.9, prompt trong `src/task10_generation.py` |
| Embedding model                    | `BAAI/bge-m3` (sentence-transformers, CPU), ChromaDB cosine, 985 chunks |
| Corpus version/commit              | `0fb3190` (5 PDF legal + 10 bài news, chuẩn hoá Markdown); config C chạy tại `0a63929`, config D tại `dd89acd`, cùng corpus và index |
| Golden dataset size                | 20 câu (`golden_dataset.json`), 12 tiếng Anh + 8 tiếng Việt, 6 nhóm: criteria, requirements, scoring, band_descriptor (8 câu), task_format, advice |
| `top_k`                            | 5 (RRF lấy 10 ứng viên mỗi nhánh rồi cắt còn 5; config C giữ 10 sau RRF rồi cross-encoder cắt còn 5) |
| Fallback threshold and calibration | Cosine dense top-1 ≥ 0.53 thì dùng hybrid, dưới thì thử PageIndex. Hiệu chỉnh bằng 6 query in-domain (min 0.5907) và 6 query out-of-domain (max 0.4714), chọn giữa khoảng trống. Trong run này **0/20** câu golden rơi xuống fallback (dense top-1 thấp nhất 0.631). |

Số liệu chi tiết từng câu, context đã lấy, latency và câu trả lời nằm trong `results/config_{A,B,C,D}.json`, tổng hợp ở `results/summary.md`. Chạy lại bằng `python -m src.task11_evaluation` (A+B+C+D) hoặc `--config D`.

## Configurations

- **Config A — dense-only:** `semantic_search(query, top_k=10)` bằng bge-m3 trên ChromaDB, cắt còn 5 chunk đầu theo cosine; không chạy BM25, không RRF (`retrieve_detailed(..., use_reranking=False)`).
- **Config B — hybrid + RRF:** `semantic_search` + `lexical_search` (BM25Okapi trên cùng 985 chunk), mỗi nhánh 10 ứng viên, gộp bằng `rerank_rrf` (k=60) đúng một lần, lấy 5 chunk đầu (`use_reranking=True`). Đây là so sánh A/B bắt buộc.
- **Config C — hybrid + RRF + rerank (bonus):** như B nhưng RRF giữ 10 ứng viên, cross-encoder `BAAI/bge-reranker-v2-m3` (`src/task12_cross_encoder_rerank.py`, chạy CPU) chấm lại cặp (query, chunk) rồi cắt còn 5 (`use_cross_encoder=True`). Cross-encoder chỉ sắp xếp lại danh sách RRF, không thêm ứng viên; fallback vẫn quyết định bằng cosine dense trước khi rerank. Cấu hình này là baseline cho HyDE.

- **Config D — C + HyDE (bonus):** như C nhưng query tìm kiếm được nối thêm đoạn giả định do gpt-4o-mini viết theo văn phong band descriptor (`src/task14_hyde.py`). RRF gộp **3** danh sách trong một lần gọi: dense(query gốc), dense(query + hypothetical), BM25(query + hypothetical); giữ dense gốc để phòng đoạn giả định lạc đề. Fallback vẫn dùng cosine của query gốc nên threshold 0.53 không đổi. Đoạn giả định chỉ dùng để tìm, không đưa vào Context của Task 10. **Đây là cấu hình mặc định của chatbot** (`RERANKER_ENABLED=1`, `HYDE_ENABLED=1`).

Các config phải dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy. Tất cả đi qua cùng ngưỡng fallback và cùng bước reorder + citation check trong `generate_from_chunks`.

## Overall scores

| Metric            | Config A | Config B | Config C (bonus) | Config D (bonus) | Delta B−A | Delta C−B | Delta D−C |
| ----------------- | -------: | -------: | ---------------: | ---------------: | --------: | --------: | --------: |
| Faithfulness      |   0.6833 |   0.7000 |           0.7536 |           0.8333 |   +0.0167 |   +0.0536 |   +0.0797 |
| Answer relevance  |   0.6128 |   0.5802 |           0.6352 |           0.7506 |   −0.0326 |   +0.0550 |   +0.1154 |
| Context recall    |   0.7881 |   0.8476 |           0.8393 |           0.9101 |   +0.0595 |   −0.0083 |   +0.0708 |
| Context precision |   0.7767 |   0.6160 |           0.8675 |           0.9049 |   −0.1607 |   +0.2515 |   +0.0374 |
| **Average**       |   0.7152 |   0.6860 |           0.7739 |           0.8497 |   −0.0292 |   +0.0879 |   +0.0758 |

Ghi chú cách đọc: safe refusal được chấm faithfulness = 0 và relevance = 0 (câu trả lời không chứa nội dung), nên hai metric này bị kéo xuống trực tiếp bởi số câu refusal: A 5/20, B 6/20, C 4/20, D 2/20. Nếu chỉ tính các câu có trả lời, faithfulness A = 0.911 (15 câu), B = 1.000 (14 câu), C = 0.942 (16 câu), D = 0.926 (18 câu); precision A = 0.923, B = 0.747, C = 0.992, D = 0.948.

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
|        2 | **Đã làm (Config C, mục Bonus experiments).** Thêm reranker (bge-reranker hoặc Jina) sau RRF: lấy 10 ứng viên hybrid, rerank cross-encoder, cắt 5. | Precision B thấp hơn A 0.16 do BM25 đưa chunk khớp từ khoá nhưng không liên quan (g08, g17, g05); RRF chỉ gộp thứ hạng, không nhìn nội dung. | Precision B lên ngang A (~0.78) mà vẫn giữ recall của hybrid. | Đã chạy: precision 0.616 → 0.868 (vượt A 0.777), recall 0.848 → 0.839 (−0.008). Kết luận đúng với dự đoán. |
|        3 | Ổn định generation: temperature 0 cho generator và cho phép LLM trả lời khi context đủ nhưng citation lệch format (đã có `normalize_citations`); log câu trả lời thô trước khi refusal để phân loại refusal thật/giả. | g18 (B) refusal dù recall 1.0; cùng input chạy 6 lần thì 2 lần citation sai format, 1 lần refusal. | Loại bỏ refusal giả do generation; faithfulness B ≥ 0.75. | Chạy g18 và 5 câu refusal 5 lần mỗi câu, tỉ lệ refusal trên câu có context đúng phải = 0. |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Reranker cross-encoder `bge-reranker-v2-m3` sau RRF (Config C, `src/task12_cross_encoder_rerank.py`) | Config B (hybrid + RRF) | Precision +0.2515 (0.616 → 0.868), faithfulness +0.054, relevance +0.055, recall −0.008; average +0.088 (0.686 → 0.774), cao nhất trong 3 config. Refusal 6 → 4: g16 (bullet points) và g18 (cách tính điểm) từ refusal thành trả lời đúng vì cross-encoder đẩy chunk trả lời lên top-5 (g16 precision 0.00 → 1.00, g18 0.33 → 1.00). Precision tăng ở 15/20 câu, chỉ giảm ở g07 (0.33 → 0.20). | Retrieval median 113 ms → 4 471 ms (chạy CPU macOS Intel, 10 cặp query–chunk mỗi câu; lần đầu thêm ~5 s load model). Không tốn API vì model local; generation không đổi. | **Reranker chứng minh cải thiện so với RRF** trên cùng golden set, đúng recommendation #2 ở trên: lấy lại precision mà hybrid đánh mất mà không giảm recall đáng kể. Nhóm bật mặc định cho chatbot (`RERANKER_ENABLED=1`). 4 refusal còn lại (g07, g09, g10, g13) vẫn là câu "Band N + tiêu chí" — reranker không cứu được vì chunk đúng không có trong 10 ứng viên RRF (lỗi chunking, recommendation #1). |
| HyDE (Config D = C + HyDE, `src/task14_hyde.py`) | Config C (hybrid + RRF + rerank) | Average +0.0758 (0.774 → 0.850): faithfulness +0.080, relevance +0.115, recall +0.071, precision +0.037 — cả 4 metric đều tăng. Refusal 4 → 2: **g10** (Grammatical Range Band 5) và **g13** (so sánh Lexical Resource Band 8/9) từ refusal thành trả lời đúng có citation; đây là hai câu "Band N + tiêu chí" mà BM25 bigram và cross-encoder đều không cứu được vì chunk đúng không lọt top-10 RRF. Đoạn giả định viết theo văn phong descriptor ("limited range of grammatical structures… errors are frequent") nên dense trên query mở rộng kéo được chunk descriptor thật lên. Recall tăng ở 3 câu (g07, g10, g15), giảm ở 1 (g09). | Thêm 1 lời gọi gpt-4o-mini + 1 dense + 1 BM25 mỗi query: retrieval median 4.5 s → 6.0 s (CPU). Generation không đổi. | **HyDE chứng minh cải thiện** trên cùng golden set và cùng baseline mạnh nhất (C). Nhóm bật mặc định (`HYDE_ENABLED=1`). Còn 2 refusal (g07, g09): chunk đúng vẫn không lọt top-10 — cần sửa chunking (recommendation #1). |
| Conversation memory cho follow-up (`src/task13_conversation_memory.py`) | Không có memory: câu "And for Task 1?" được retrieval nguyên văn, không biết đang hỏi về số từ | Demo 3 lượt (`results/memory_demo.md`, config C): "And for Task 1?" → viết lại thành "And for IELTS Writing Task 1, how many words must I write?" → trả lời đúng 150 từ có citation; "Which one carries more weight in the final score?" → "Which one, IELTS Writing Task 1 or Task 2, carries more weight…" → trả lời đúng Task 2. Không đo trên golden set vì golden là câu đơn lẻ. | Thêm 1 lời gọi gpt-4o-mini (condense) mỗi lượt có lịch sử, ~0.5–1 s; lượt đầu không tốn. | Tính năng chạy được, có transcript; bật mặc định trong Streamlit (toggle "Nhớ hội thoại"), 6 test offline. Citation vẫn chỉ lấy từ Context hiện tại, lịch sử đã bỏ citation cũ nên không sinh refusal giả. |
| UI citation/source highlighting (`src/ui_citations.py`, `app.py`) | UI cũ: citation thô `[news/x.md::chunk-48]` trong câu trả lời, 5 nguồn liệt kê ngang nhau, người dùng phải tự tìm câu bằng chứng | Không có metric; bằng chứng là ảnh `docs/ui_citation_highlight.png` và `docs/ui_conversation_memory.png`: citation thành badge số có tooltip chunk ID, nguồn được cite xếp trước và đánh số khớp, câu bằng chứng trong chunk bôi vàng (trên 16 câu trả lời của config C: 15/16 chunk được cite có ít nhất một câu được đánh dấu, 51/117 câu), nguồn không cite hiển thị mờ. | Thuần Python, không thêm lời gọi LLM hay độ trễ đáng kể. | Tính năng chạy được, 6 test offline. Heuristic trùng từ khoá + số nên có thể highlight thừa/thiếu khi answer tiếng Việt còn chunk tiếng Anh. |
| PageIndex fallback | — | — | — | Đã tích hợp (Task 8) nhưng không kích hoạt trên golden set (0/20, dense top-1 thấp nhất 0.631 > 0.53) nên chưa đo được. |
