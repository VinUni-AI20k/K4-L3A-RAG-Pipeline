# Individual contribution report

## Thông tin

- Họ và tên: Phạm Quang Đạt
- Mã học viên: 2A202602704
- Nhóm: K4-L3A
- Repository/branch: https://github.com/vuanh259/K4-L3A-RAG-Pipeline/tree/quangdat

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Lexical Search (Task 6) | Xây dựng thuật toán tìm kiếm từ khóa chính xác BM25Okapi trên cùng tập corpus chunks của Task 4, bổ sung cơ chế tie-breaker | `src/task6_lexical_search.py` | Done |
| Hybrid RRF Reranking (Task 7) | Triển khai thuật toán Reciprocal Rank Fusion với hằng số $k=60$ để hợp nhất bảng xếp hạng Dense và BM25 | `src/task7_reranking.py` | Done |
| Golden Dataset Creation | Xây dựng bộ dữ liệu vàng kiểm thử gồm 15 ca câu hỏi - đáp - ngữ cảnh Tiếng Việt chuẩn xác bám sát thực tế bài thi IELTS Writing | `group_project/evaluation/golden_dataset.json` | Done |
| RAG Evaluation & RESULT.md | Thiết kế và thực hiện đánh giá thực nghiệm A/B Testing so sánh Dense-only vs Hybrid RRF theo 4 chỉ số Ragas, hoàn thiện báo cáo phân tích lỗi | `group_project/evaluation/RESULT.md`, `reports/RESULT.md` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Áp dụng thuật toán Reciprocal Rank Fusion (RRF, $k=60$) để kết hợp kết quả tìm kiếm thay vì dùng phương pháp cộng gộp tuyến tính điểm số có trọng số ($\alpha \cdot \text{Dense} + (1-\alpha) \cdot \text{BM25}$).
   **Lý do/evidence:** Thang đo của Cosine Similarity thuộc đoạn $[0, 1]$, trong khi thang điểm của BM25 không bị chặn trên $[0, +\infty)$ và phụ thuộc mạnh vào độ dài câu hỏi/độ dài tài liệu. Nếu chuẩn hóa min-max (Min-Max Scaling), điểm số rất dễ bị méo mó khi gặp từ khóa hiếm. RRF xếp hạng thuần túy theo vị trí $\sum \frac{1}{60 + \text{rank}}$, giúp cải thiện Context Recall từ 0.80 lên 0.92 và Context Precision từ 0.78 lên 0.91.
   **Trade-off:** RRF score chỉ phản ánh thứ tự ưu tiên tương đối, không thể dùng làm thước đo độ tin cậy tuyệt đối để kích hoạt fallback (đã bàn giao Task 9 dùng riêng điểm cosine gốc để fallback).

2. **Quyết định:** Bổ sung cơ chế giải quyết điểm hòa (tie-breaker) `match_count * 1e-4` trong hàm `lexical_search`.
   **Lý do/evidence:** Khi chạy kiểm thử hợp đồng trong `tests/test_contracts.py`, tập corpus test giả lập chỉ có 2 documents ($N=2$). Khi một từ khóa xuất hiện ở 1 trong 2 tài liệu, công thức IDF của BM25Okapi cho kết quả $\ln((2 - 1 + 0.5) / (1 + 0.5)) = \ln(1) = 0.0$, làm toàn bộ điểm số của các văn bản bằng 0 và không thể phân loại. Bổ sung `match_count * 1e-4` giúp các văn bản khớp từ khóa được xếp lên trước mà không làm ảnh hưởng đến điểm BM25 thực tế.
   **Trade-off:** Thêm một vòng lặp nhỏ đếm số từ trùng lặp trên tập kết quả top_k, thời gian tính toán thêm $< 1\text{ms}$.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: `pytest tests/test_contracts.py -k "test_lexical or test_rrf"` và `pytest tests/test_acceptance.py -k "test_golden or test_evaluation"`.
- Kết quả trước/sau nếu có: Ban đầu `test_golden_dataset_has_15_grounded_cases` và `test_evaluation_report_is_completed` bị FAIL do file rỗng và còn chữ TODO; sau khi hoàn thiện dữ liệu và báo cáo, toàn bộ các bài test đều PASS 100%.
- Lỗi đã phát hiện và cách xử lý: Nhận diện hiện tượng mô hình Dense Search thuần túy bị nhầm lẫn giữa tiêu chí của Band 6 và Band 7 khi câu hỏi nhắc đến band cụ thể; BM25 đã giải quyết triệt để lỗi này bằng cách chấm điểm cao vượt trội cho văn bản chứa chính xác từ khóa "Band 7".

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Hiện tại BM25Okapi sử dụng phép tách từ đơn giản bằng khoảng trắng (`.split()`), chưa áp dụng stemming (đưa từ về gốc như *describing* $\to$ *describe*) hay loại bỏ stop words tiếng Anh.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Tích hợp thư viện NLTK hoặc spaCy để tiền xử lý lemmatization cho BM25 nhằm tăng khả năng nhận diện các biến thể của từ vựng.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Phạm Quang Đạt
