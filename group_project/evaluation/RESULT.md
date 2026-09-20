# RAG evaluation results

Mọi con số trong file này do `group_project/evaluation/eval_pipeline.py` sinh ra
từ một lần chạy thật trên golden dataset. Không có giá trị nào được điền tay.

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | Ragas 0.1.21 |
| Evaluator model                    | deepseek-chat (deepseek) |
| Generator model                    | deepseek-chat (deepseek) |
| Embedding model                    | paraphrase-multilingual-MiniLM-L12-v2 (sentence_transformers) |
| Corpus version/commit              | 3 legal PDF + 5 news JSON, 16 chunks |
| Golden dataset size                | 15 |
| `top_k`                            | 5 |
| Fallback threshold and calibration | 0.35 — đo trên 8 query in-domain (0.360–0.791) và 8 query out-of-domain (0.135–0.336) |

## Configurations

- **Config A — dense-only:** `retrieve(use_reranking=False)` — chỉ lấy top-k từ ChromaDB theo cosine similarity.
- **Config B — hybrid + RRF:** `retrieve(use_reranking=True)` — fuse dense và BM25 bằng RRF (k=60), đúng một lần.

Hai config dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric | Config A | Config B | Delta B−A |
| ------ | -------: | -------: | --------: |
| Faithfulness | 0.939 | 0.961 | +0.022 |
| Answer relevance | 0.858 | 0.864 | +0.006 |
| Context recall | 1.000 | 1.000 | +0.000 |
| Context precision | 0.967 | 0.963 | -0.003 |
| **Average** | 0.941 | 0.947 | +0.006 |

## A/B comparison

- Cấu hình tốt hơn: **B (hybrid + RRF)** (chênh lệch average +0.006).
- Evidence: bảng Overall scores ở trên; điểm từng câu nằm trong `per_question_scores.json`.
- Trade-off về latency/cost: Config B chạy thêm một lượt BM25 trên bộ chunks đã nạp sẵn trong RAM cộng một lượt fuse O(n log n), không phát sinh lời gọi API nào. Chi phí token của hai config bằng nhau vì cùng `top_k`.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| -: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------- | ---------- |
| 1 | Nếu người bán từ chối yêu cầu trả hàng thì ai giải quyết? | A (dense-only) | 0.667 | 0.837 | 1.000 | 0.500 | retrieval | xem phần Recommendations bên dưới |
| 2 | Thanh toán bằng thẻ tín dụng trên Shopee có an toàn không? | A (dense-only) | 0.667 | 0.573 | 1.000 | 1.000 | retrieval | xem phần Recommendations bên dưới |
| 3 | Thanh toán bằng thẻ tín dụng trên Shopee có an toàn không? | B (hybrid + RRF) | 0.667 | 0.638 | 1.000 | 1.000 | retrieval | xem phần Recommendations bên dưới |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
| 1 | Thêm ngưỡng cắt score trong `retrieve()`, hoặc giảm `top_k` xuống 3, thay vì luôn trả đủ `top_k` chunk | Câu "Thanh toán bằng thẻ tín dụng có an toàn không?" lấy 5 chunk nhưng chỉ chunk 1 (`payment-methods-shopee.md`) liên quan; 4 chunk còn lại nói về trả hàng, giao hàng và đổi phương thức thanh toán. Corpus chỉ có 16 chunk nên `top_k=5` ép lấy cả phần không liên quan. Câu "người bán từ chối yêu cầu trả hàng" có context precision 0.500 vì lý do tương tự | Context precision tăng; context nhiễu ít đi thì faithfulness cũng đỡ bị kéo xuống | Chạy lại `eval_pipeline.py` và so cột Context precision với bảng hiện tại (A 0.967 / B 0.963) |
| 2 | Sửa `SYSTEM_PROMPT`: cấm mở đầu bằng "Có." / "Không." đứng riêng thành một câu, bắt gộp vào mệnh đề có citation | Hai case faithfulness thấp nhất (0.667) thực ra **trả lời đúng và có citation**: "Có. Mọi giao dịch qua thẻ đều được mã hóa… [Document 1]". Ragas tách answer thành từng statement rồi đối chiếu context, nên "Có." trở thành một statement không kiểm chứng được và ăn 1/3 điểm faithfulness | Faithfulness tăng mà không phải đổi gì ở retrieval — đây là lỗi đo, không phải lỗi hệ thống | Chạy lại evaluation, xem 2 câu này trong `per_question_scores.json` có lên 1.000 không |
| 3 | Mở rộng corpus và golden dataset trước khi kết luận hybrid tốt hơn dense | Delta average B−A chỉ **+0.006** trên 15 câu, và context precision của B còn thấp hơn A (−0.003). Với corpus 8 tài liệu / 16 chunk thì dense gần như luôn lấy trúng, BM25 hầu như không thêm được gì để RRF phát huy | Có đủ dữ liệu để kết luận A/B một cách có nghĩa, thay vì chênh lệch nằm trong nhiễu | Lặp lại A/B trên corpus lớn hơn và xem delta có vượt khỏi mức dao động giữa các lần chạy không |

**Lưu ý về độ tin cậy của toàn bộ bảng điểm:** corpus là synthetic, 8 tài liệu,
16 chunk, và golden dataset 15 câu đều được soạn từ chính corpus đó. Điểm cao ở
đây chỉ chứng minh pipeline nối đúng từ đầu tới cuối, không chứng minh hệ thống
hoạt động tốt trên tài liệu thật.

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| — | — | — | — | Chưa chạy |
