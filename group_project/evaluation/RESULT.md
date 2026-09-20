# RAG evaluation results

## Run information

| Field | Value |
|---|---|
| Evaluation date | 2026-09-20 |
| Framework and version | Custom reproducible runner (`src/evaluate.py`), Google Gen AI SDK 1.x |
| Evaluator model | Gemini 3.5 Flash Lite |
| Generator model | Gemini 3.5 Flash Lite |
| Embedding model | Gemini Embedding 001 |
| Corpus version/commit | 8 documents (3 legal, 5 news), base commit `2560bc4` |
| Golden dataset size | 15 grounded questions |
| `top_k` | 5 (candidate pool 10) |
| Fallback threshold and calibration | 0.82; in-domain samples 0.832–0.904, out-of-domain samples 0.753–0.819 |

Raw per-case answers, retrieved chunk IDs and scores are stored in `evaluation_results.json`.

## Configurations

- **Config A — dense-only:** Gemini query embedding, cosine search in Chroma, top 5 chunks.
- **Config B — hybrid + RRF:** top 10 dense plus top 10 BM25, fused once with RRF (`k=60`), top 5 chunks.

Both configurations used the same dataset, generator, evaluator, system prompt and `top_k`.

## Overall scores

| Metric | Config A | Config B | Delta B−A |
|---|---:|---:|---:|
| Faithfulness | 0.978 | 1.000 | +0.022 |
| Answer relevance | 1.000 | 1.000 | +0.000 |
| Context recall | 0.960 | 0.960 | +0.000 |
| Context precision | 0.473 | 0.430 | -0.043 |
| **Average** | **0.853** | **0.848** | **-0.005** |

## A/B comparison

- Cấu hình tốt hơn trên bộ test hiện tại: **dense-only**, chênh 0.005 điểm trung bình.
- Evidence: hybrid đạt faithfulness tuyệt đối và sửa lỗi faithfulness ở câu mùa hoa Hà Giang, nhưng đưa thêm chunks ít liên quan nên context precision giảm 0.043.
- Trade-off: hybrid thêm BM25 và RRF nên tăng CPU/latency nhỏ, không tăng số lần gọi Gemini; dense-only đơn giản và có precision cao hơn trên câu hỏi ngữ nghĩa tự nhiên.
- Kết luận: giữ hybrid làm pipeline sản phẩm vì bền vững hơn với tên riêng/từ khóa chính xác, nhưng cần lọc hậu RRF theo relevance trước khi generation.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
|---:|---|---|---:|---:|---:|---:|---|---|
| 1 | Những món đặc sản tiêu biểu nào được nhắc đến ở Hà Giang? | hybrid | 1.00 | 1.00 | 0.40 | 0.50 | retrieval/data | Danh sách món nằm rải ở nhiều chunks; `top_k=5` chưa bao phủ đủ expected answer. |
| 2 | Hà Giang nổi tiếng với mùa hoa tam giác mạch vào khoảng thời gian nào? | dense | 0.67 | 1.00 | 1.00 | 0.25 | generation/retrieval | Context có đáp án nhưng nhiều đoạn nhiễu làm model thêm chi tiết chưa được hỗ trợ đầy đủ. |
| 3 | Đi tàu cao tốc từ Hà Tiên ra Phú Quốc mất bao lâu? | dense | 1.00 | 1.00 | 1.00 | 0.20 | retrieval | Một chunk đúng trong năm chunks; bốn chunks còn lại không cần thiết. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
|---:|---|---|---|---|
| 1 | Thêm relevance cutoff hoặc reranker sau RRF | Hybrid precision thấp hơn dense 0.043 | Tăng context precision, giảm nhiễu prompt | Chạy lại cùng 15 câu và yêu cầu precision > 0.473 |
| 2 | Chunk theo heading và gom danh sách liền mạch | Câu đặc sản Hà Giang chỉ recall 0.40 | Tăng recall cho câu hỏi tổng hợp | Thêm 5 câu list-type, đo recall |
| 3 | Mở rộng calibration với ít nhất 20 câu ngoài miền | Biên OOD cao nhất 0.819 sát threshold 0.82 | Safe refusal ổn định hơn | Báo cáo confusion matrix in/out-domain |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
|---|---|---:|---:|---|
| Citation/source highlighting trong Streamlit | Text-only chat | Chưa chấm bằng metric tự động | Không thêm API call | Đã triển khai; giúp đối chiếu từng chunk, URL, method và score. |

## Methodology limitations

Các điểm số do cùng một Gemini model làm judge nên có thể thiên lệch và không thay thế đánh giá con người. Bộ golden nhỏ, chủ yếu là câu hỏi fact ngắn; chưa đại diện đầy đủ cho multi-hop, câu mơ hồ hoặc hội thoại nhiều lượt. Kết quả cần được tái chạy khi corpus/prompt/model thay đổi.
