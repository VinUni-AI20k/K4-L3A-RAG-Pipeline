# Individual contribution report

## Thông tin

- Họ và tên: Trần Anh Quân
- Mã học viên: [Điền mã học viên nếu có]
- Nhóm: L3A (K4-L3A)
- Repository/branch: https://github.com/thangws4/K4-L3A-RAG-Pipeline / branch `tran_anh_quan`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 5 — Semantic Search (Dense Retrieval) | Triển khai hàm `semantic_search` truy vấn vector từ ChromaDB (`hnsw:space: cosine`), chuyển đổi cosine distance thành similarity score ($1 - \text{distance}$), định dạng dữ liệu trả về theo contract `SearchResult`, sắp xếp giảm dần và cắt `top_k`. | `src/task5_semantic_search.py`<br>Commit `36aaa83` | Done |
| Task 6 — Lexical Search (BM25) | Triển khai bộ tìm kiếm từ khóa BM25 với lớp `SafeBM25Okapi` (áp dụng công thức làm mịn Lucene IDF) nhằm tránh lỗi IDF bằng 0 hoặc âm trên tập văn bản nhỏ; triển khai cơ chế index caching singleton và trả về đúng contract `SearchResult`. | `src/task6_lexical_search.py`<br>Commit `36aaa83` | Done |
| Task 7 — Reranking (Hybrid Search / RRF) | Triển khai thuật toán Reciprocal Rank Fusion (RRF) kết hợp kết quả từ Dense và BM25 theo công thức $RRF(d) = \sum \frac{1}{60 + \text{rank}}$; merge metadata và chuẩn hóa `retrieval_method="hybrid"`, sắp xếp giảm dần theo điểm RRF. | `src/task7_reranking.py`<br>Commit `36aaa83` | Done |
| Testing & Verification (Tầng Retrieval) | Chạy và pass toàn bộ contract tests của Task 5, 6, 7 trong test suite của dự án (`tests/test_contracts.py`); kiểm tra tính tương thích dữ liệu và tính ổn định của pipeline. | `tests/test_contracts.py`<br>Commit `36aaa83` | Done |

Chỉ kê khai công việc có thể đối chiếu bằng file, commit, pull request, test hoặc kết quả evaluation.

## Quyết định kỹ thuật quan trọng

Mô tả tối đa hai quyết định mà bạn trực tiếp tham gia:

1. **Quyết định: Sử dụng công thức làm mịn Lucene IDF (`SafeBM25Okapi`) cho BM25 thay vì `BM25Okapi` mặc định của `rank-bm25`.**  
   **Lý do/evidence:** Thư viện `rank-bm25` mặc định tính IDF theo công thức Robertson-Spärck Jones: $\text{IDF} = \ln\left(\frac{N - n + 0.5}{n + 0.5}\right)$. Khi một từ xuất hiện trong đúng nửa số tài liệu (ví dụ $N=2, n=1$ như trong test case `test_task6_empty_query_or_missing_terms`), tử số bằng mẫu số khiến $\text{IDF} = \ln(1) = 0.0$, dẫn đến điểm BM25 bằng 0 và test bị fail. Tôi đã chuyển sang kế thừa và ghi đè bằng công thức Lucene: $\text{IDF} = \ln\left(1 + \frac{N - n + 0.5}{n + 0.5}\right)$, đảm bảo điểm số luôn dương đối với các từ khóa khớp.  
   **Trade-off:** Điểm số tuyệt đối thay đổi nhẹ so với BM25 nguyên bản, nhưng tính chất bảo toàn thứ tự xếp hạng (monotonicity) được giữ nguyên 100%, đồng thời đảm bảo hệ thống luôn trả về điểm hợp lệ.

2. **Quyết định: Chuẩn hóa Cosine Distance sang Similarity Score ($1 - \text{distance}$) và dùng RRF thay vì Score Fusion ở bước Reranking.**  
   **Lý do/evidence:** ChromaDB cấu hình `{"hnsw:space": "cosine"}` trả về khoảng cách cosine distance ($D \in [0, 2]$). Để tuân thủ contract `SearchResult` (yêu cầu điểm càng cao càng liên quan), tôi chuẩn hóa $score = 1.0 - distance$ (kẹp trong $[0.0, 1.0]$). Ở bước kết hợp tại Task 7, do điểm Dense là cosine similarity $[0, 1]$ còn điểm BM25 là điểm không bị chặn trên, việc dùng Reciprocal Rank Fusion (RRF với $k=60$) dựa trên thứ hạng (ranks) giúp kết hợp công bằng hai bộ tìm kiếm mà không cần bước chuẩn hóa phân phối điểm số phức tạp.  
   **Trade-off:** RRF bỏ qua độ chênh lệch điểm số tuyệt đối giữa các thứ hạng lân cận, nhưng đem lại độ bền vững (robustness) và ổn định cao trên đa dạng các loại câu hỏi (cả câu hỏi tự nhiên lẫn câu hỏi tra cứu chính xác số hiệu điều luật).

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - Chạy toàn bộ test contract của tầng retrieval: `pytest tests/test_contracts.py -k "task5 or task6 or task7" -v`
  - Thử nghiệm query ngữ nghĩa: `"quy định về trừ điểm giấy phép lái xe"`, `"mức phạt nồng độ cồn"`
  - Thử nghiệm query từ khóa chính xác: `"Nghị định 236/2026/NĐ-CP"`, `"Điều 27"`, `"Khoản 14"`
- Kết quả trước/sau nếu có:
  - Trước: Các file task 5, 6, 7 chỉ có khung hàm mẫu (`pass` hoặc `NotImplementedError`), unit test fail.
  - Sau: Toàn bộ contract tests đều PASS (4/4 test cases của Task 5, 6, 7 đạt chuẩn). Kết quả RRF hybrid kết hợp đầy đủ ưu thế của cả tìm kiếm từ khóa chính xác và tìm kiếm ngữ nghĩa theo ngữ cảnh.
- Lỗi đã phát hiện và cách xử lý:
  - Phát hiện lỗi BM25 trả về điểm 0 khi từ khóa xuất hiện ở 50% văn bản: Đã xử lý triệt để bằng `SafeBM25Okapi`.
  - Phát hiện metadata trả về từ ChromaDB có thể chứa chuỗi rỗng thay cho `None`: Đã map và format chuẩn theo dataclass `SearchResult`.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Bộ tách từ cho BM25 hiện tại đang sử dụng regex tách từ cơ bản theo khoảng trắng/ký tự đặc biệt, chưa áp dụng bộ tách từ ghép tiếng Việt chuyên dụng (như `pyvi` hay `underthesea`) nên chưa tận dụng tối đa các cụm từ pháp lý phức tạp.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Bổ sung word segmentation tiếng Việt cho BM25 và tích hợp Cross-Encoder Reranker (như `bge-reranker-large`) sau bước RRF để tinh chỉnh lại độ chính xác ngữ nghĩa của top 5 kết quả trước khi đưa vào LLM sinh câu trả lời.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Trần Anh Quân
