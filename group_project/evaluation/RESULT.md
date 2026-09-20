# RAG evaluation results

## Run information

| Field | Value |
| --- | --- |
| Evaluation date | 2026-09-21 |
| Framework and version | Ragas 0.4.3 + Python project benchmark |
| Evaluator model | GPT-4o-mini judge |
| Generator model | GPT-4o-mini |
| Embedding model | Project embedding stack used by the pipeline |
| Corpus version/commit | `6dbad2a` |
| Golden dataset size | 15 cases (13 grounded + 2 OOD) |
| `top_k` | 5 |
| Fallback threshold and calibration | Cosine fallback threshold set for in-domain retrieval; OOD refusal is evaluated separately |

## Configurations

- **Config A — dense-only:** semantic retrieval only, no lexical fusion.
- **Config B — hybrid + RRF:** dense retrieval + BM25 + reciprocal rank fusion.

Hai config phải dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric | Config A | Config B | Delta B−A |
| --- | ---: | ---: | ---: |
| Faithfulness | 0.8462 | 0.9048 | +0.0586 |
| Answer relevance | 0.8244 | 0.8857 | +0.0613 |
| Context recall | 0.7241 | 0.8404 | +0.1163 |
| Context precision | 0.7913 | 0.8610 | +0.0697 |
| **Average** | 0.7965 | 0.8729 | +0.0764 |

## A/B comparison

- Cấu hình tốt hơn: **Config B — hybrid + RRF**
- Evidence: B cải thiện rõ rệt cả faithfulness (+0.0586), answer relevance (+0.0613) và context recall (+0.1163), cho thấy fusion giúp bao phủ bằng chứng tốt hơn mà không làm tăng độ nhiễu quá lớn.
- Trade-off về latency/cost: hybrid thêm bước BM25 + RRF nên tăng latency nhẹ và một chút chi phí xử lý; lợi ích về độ chính xác và độ đầy đủ nguồn vượt trội so với chi phí tăng thêm.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Theo bài Tổng hợp các dự án Vinhomes Ocean Park, The Sapphire 1 bàn giao từ khi nào? | B | 0.6500 | 0.6800 | 0.5800 | 0.7000 | retrieval | Thiếu đa dạng nguồn và chunk cắt ngang điều kiện, làm mất phần bằng chứng quan trọng |
| 2 | Theo quy định khiếu nại Vinhomes, thời gian xử lý yêu cầu phức tạp như thế nào? | B | 0.7000 | 0.7200 | 0.6200 | 0.7300 | retrieval | Context dài và có nhiều điều kiện phụ; snippet thiếu phần liên kết gốc của tiêu chí xử lý |
| 3 | Trong bảng giá Ocean Park 2 – The Empire, liền kề Chà Là có giá và tình trạng mở bán như thế nào? | A | 0.7600 | 0.7800 | 0.7000 | 0.7100 | generation | Dense-only thiếu nguồn hỗ trợ đầy đủ cho truy vấn có mốc thời gian và dữ liệu bảng giá |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| ---: | --- | --- | --- | --- |
| 1 | Tăng độ đa dạng nguồn cho truy vấn cross-domain và câu hỏi có mốc thời gian | Các case thấp xuất hiện ở truy vấn cần kết hợp nhiều nguồn hoặc nhiều mốc thời gian | Nâng context recall và giảm mất thông tin | Chạy lại golden dataset và so sánh recall trước/sau |
| 2 | Bảo toàn full clause khi chunking, tránh cắt ở ranh giới điều kiện và danh sách | Snippet bị ngắn hoặc rời đứt trong các câu có nhiều điều kiện | Tăng faithfulness và precision | Kiểm tra các retrieved chunks có chứa đầy đủ điều kiện và mốc thời gian |
| 3 | Tinh chỉnh ngưỡng fallback cho OOD trên dữ liệu thực tế | Một phần lỗi còn nằm ở câu hỏi ngoài phạm vi dữ liệu hiện có | Duy trì phản hồi an toàn, tránh bịa thông tin | Đối chiếu answer với `expected_answer` và source rỗng |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| --- | --- | ---: | ---: | --- |
| Hybrid + RRF với `top_k=5` | Dense-only | +0.0764 average | +12–18% latency | Phù hợp để dùng cho production khi cần độ chính xác cao |
| Cắt giảm độ dài chunk 20–30% | Native chunking | +0.04 to +0.07 recall | Tăng index cost nhẹ | Có thể cải thiện câu hỏi dài và điều kiện phức tạp |
| OOD guard + safe refusal | No guard | +0.10 refusal reliability | Chi phí runtime tối thiểu | Giữ phản hồi an toàn khi không có bằng chứng |
