# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | Chưa chạy benchmark; golden dataset được thiết kế ngày 2026-09-20 |
| Framework and version              | Ragas 0.4.3 dự kiến; chưa thực thi evaluator |
| Evaluator model                    | Chưa cấu hình cho lần benchmark chính thức |
| Generator model                    | Provider/model được đọc từ `.env`; không ghi khóa hoặc model riêng tư vào báo cáo |
| Embedding model                    | `BAAI/bge-m3`, 1024 chiều |
| Corpus version/commit              | Working-tree snapshot ngày 2026-09-20, gồm 3 văn bản pháp lý và 10 bài viết |
| Golden dataset size                | 18 câu hỏi có đáp án và context đối chiếu nguồn |
| `top_k`                            | 5 |
| Fallback threshold and calibration | Mặc định 0.3; cần hiệu chỉnh bằng tập in-domain/out-of-domain trước benchmark |

## Configurations

- **Config A — dense-only:** `retrieve(..., use_reranking=False)`, cùng embedding, generator, prompt và `top_k=5`.
- **Config B — hybrid + RRF:** dense + BM25, fuse RRF một lần với `k=60`, PageIndex fallback theo cosine dense.

Golden dataset có 12 câu pháp lý/chính sách và 6 câu du lịch ẩm thực. Các cấu hình phải dùng cùng dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

Các chỉ số dưới đây chưa được đo. Báo cáo không điền số giả trước khi chạy cùng một evaluator trên cả hai cấu hình.

| Metric            | Config A    | Config B    | Delta B−A   |
| ----------------- | ----------: | ----------: | ----------: |
| Faithfulness      | Chưa đo     | Chưa đo     | Chưa xác định |
| Answer relevance  | Chưa đo     | Chưa đo     | Chưa xác định |
| Context recall    | Chưa đo     | Chưa đo     | Chưa xác định |
| Context precision | Chưa đo     | Chưa đo     | Chưa xác định |
| **Average**       | Chưa đo     | Chưa đo     | Chưa xác định |

## A/B comparison

- Cấu hình tốt hơn: Chưa thể kết luận khi benchmark chưa chạy.
- Evidence: Golden dataset và hai cấu hình đã được định nghĩa; chưa có output evaluator để so sánh định lượng.
- Trade-off về latency/cost: Config B thực hiện thêm BM25 và RRF; PageIndex chỉ được gọi khi cosine dense dưới ngưỡng. Cần ghi latency và số lần fallback trong lần chạy chính thức.

## Worst performers

Chưa xếp hạng failure case vì chưa có điểm theo từng câu. Sau benchmark, chọn ba câu có trung bình bốn metric thấp nhất.

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| -: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------- | ---------- |
| 1 | Chưa xác định | Chưa xác định | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa phân loại | Chờ kết quả evaluator |
| 2 | Chưa xác định | Chưa xác định | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa phân loại | Chờ kết quả evaluator |
| 3 | Chưa xác định | Chưa xác định | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa phân loại | Chờ kết quả evaluator |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
| 1 | Cài và chạy embedding/index thật trước benchmark | Môi trường phát triển chưa tạo Chroma index bằng `BAAI/bge-m3` | Có dense baseline hợp lệ | Kiểm tra collection có đủ chunk và chạy semantic smoke query |
| 2 | Hiệu chỉnh threshold bằng câu in-domain và out-of-domain | Giá trị 0.3 hiện là mặc định, chưa được hiệu chỉnh trên corpus | Giảm fallback sai và safe refusal không cần thiết | Quét nhiều threshold và so precision/recall fallback |
| 3 | Chạy A/B trên cùng 18 câu và lưu output từng case | Chưa có số đo để xác định cấu hình tốt hơn | Có bằng chứng định lượng và failure analysis | Chạy bốn metric, ghi latency rồi cập nhật bảng kết quả |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Chưa thực hiện bonus | Config B | Chưa đo | Chưa đo | Chỉ thực hiện sau khi baseline chính thức hoàn tất |
