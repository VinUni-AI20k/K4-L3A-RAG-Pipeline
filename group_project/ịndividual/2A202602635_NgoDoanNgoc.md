# Individual contribution report

## Thông tin

- Họ và tên: Ngọ Doãn Ngọc
- Mã học viên: 2A202602635
- Nhóm: Phronesis
- Repository/branch: https://github.com/nthanhwork/K4-L3A-RAG-Pipeline

## Phần việc đã thực hiện

| Module/deliverable                    | Việc tôi trực tiếp làm                                                                                                                                                                             | File/commit/PR                      | Trạng thái |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | ---------- |
| Task 7: Reranking (RRF)               | Hoàn thiện hàm `rerank_rrf()`, tính điểm theo công thức `sum(1 / (k + rank))`, copy item tránh mutating dữ liệu đầu vào, gán `retrieval_method="hybrid"`, đảm bảo deduplication và thứ tự giảm dần | `src/task7_reranking.py`            | Done       |
| Task 8: Vectorless Fallback           | Hoàn thiện `upload_documents()`, cache document IDs vào JSON, xử lý timeout và parsing kết quả theo contract `retrieval_method="pageindex"`                                                        | `src/task8_pageindex_vectorless.py` | Done       |
| Task 9: Retrieval Pipeline & Fallback | Hoàn thiện `retrieve()`: gọi dense và BM25, hợp nhất RRF đúng 1 lần, quyết định fallback dựa trên best cosine score gốc của dense search, fallback an toàn khi provider lỗi                        | `src/task9_retrieval_pipeline.py`   | Done       |
| Contract Testing & Calibration        | Kiểm thử toàn bộ contract (`test_contracts.py` 15/15 passed), hiệu chuẩn `SCORE_THRESHOLD` bằng 2 query thực nghiệm (in-domain và out-of-domain)                                                   | `tests/test_contracts.py`, `.env`   | Done       |

## Quyết định kỹ thuật quan trọng

1. **Quyết định: Dùng cosine score gốc cao nhất từ dense search để quyết định fallback thay vì RRF score**  
   **Lý do/evidence:** RRF score chỉ phản ánh thứ hạng tương đối `sum(1 / (k + rank))` với rank bắt đầu từ 1. Thang đo này phụ thuộc vào số lượng danh sách (dense + sparse) và hằng số k (thường cho điểm số nhỏ trong khoảng 0.01 - 0.035), không phản ánh mức độ tự tin ngữ nghĩa tuyệt đối của query đối với corpus. Trái lại, cosine similarity của dense retrieval phản ánh trực tiếp khoảng cách vector trong không gian biểu diễn ngữ nghĩa. Vì vậy, pipeline tách biệt rõ: dense score dùng để quyết định fallback, còn RRF chỉ dùng để hợp nhất thứ hạng.  
   **Trade-off:** Cần tạo deep copy item trong `rerank_rrf()` để không làm thay đổi item gốc, bảo toàn cosine score gốc cho pipeline đánh giá fallback.

2. **Quyết định: Thiết lập `SCORE_THRESHOLD = 0.45` qua hiệu chuẩn in-domain và out-of-domain**  
   **Lý do/evidence:** Thực nghiệm trên tập dữ liệu với embedding model `text-embedding-3-small`:
   - **Query đúng chủ đề (In-domain):** `"VAMC xử lý nợ xấu như thế nào"` -> Best dense score = **0.5208** (các chunk liên quan trực tiếp từ `legal/data_luat1.md`).
   - **Query ngoài chủ đề (Out-of-domain):** `"cách làm bánh chưng ngày tết"` -> Best dense score = **0.3438** (chunk có score cao nhất thuộc `news/article_01.md`, nội dung hoàn toàn không liên quan).
   - Ngưỡng 0.45 nằm giữa khoảng cách rõ rệt (0.3438 < 0.45 < 0.5208). Khi query in-domain, pipeline tin tưởng dense search và thực hiện RRF hybrid đúng 1 lần; khi query out-of-domain, dense score dưới 0.45 kích hoạt fallback sang PageIndex hoặc dẫn đến safe refusal ở Task 10, ngăn chặn hallucination.  
   **Trade-off:** Ngưỡng 0.45 này được hiệu chỉnh riêng cho model và corpus hiện tại. Không tuyên bố một threshold là đúng cho mọi corpus; nếu đổi sang mô hình embedding khác (như BGE-M3, Gemini) hoặc thay đổi đặc thù văn bản, ngưỡng này bắt buộc phải được hiệu chuẩn lại.

## Kiểm thử và kết quả

- **Test và query đã dùng:**
  - `pytest tests/test_contracts.py -q`: Đạt 15/15 test cases, xác nhận tính bất biến của dữ liệu, contract schema, công thức RRF, deduplication ID, fallback dựa trên dense score và pipeline sống sót khi provider lỗi.
  - `python -m src.task7_reranking`: Chạy thành công RRF hợp nhất bảng xếp hạng semantic và lexical.
  - Thử nghiệm query in-domain: `"VAMC xử lý nợ xấu như thế nào"` (best dense score: 0.5208 -> chạy RRF hybrid, top score 0.032522).
  - Thử nghiệm query out-of-domain: `"cách làm bánh chưng ngày tết"` (best dense score: 0.3438 -> dưới threshold 0.45 -> kích hoạt fallback).
- **Kết quả trước/sau:**
  - Trước: Task 8 chưa có logic upload/cache/parse; Task 7 chưa đảm bảo deep copy độc lập; `.env` bị lặp nội dung gây sai lệch định dạng; stdout cp1252 bị lỗi font tiếng Việt trên Windows console.
  - Sau: Pipeline hoạt động trơn tru, RRF tính toán chính xác, fallback hoạt động đúng nguyên lý thiết kế, toàn bộ contract test đều pass.
- **Lỗi đã phát hiện và cách xử lý:**
  - Lỗi encoding cp1252 trên Windows: Đã thêm cấu hình `sys.stdout.reconfigure(encoding="utf-8")` trong các khối execution chính.
  - Lỗi rò rỉ mutation: Thêm `copy.deepcopy()` trong `rerank_rrf()` để bảo vệ thuộc tính của item gốc.

## Điều còn hạn chế

- **Một hạn chế cụ thể:** Fallback PageIndex phụ thuộc vào API key và mạng ngoài; nếu không cấu hình key, pipeline phải dựa hoàn toàn vào cơ chế safe refusal của tầng generation khi query ngoài domain.
- **Nếu có thêm thời gian:** Tôi sẽ xây dựng cơ chế dynamic score thresholding dựa trên margin độ lệch điểm giữa top-1 và top-2 dense scores thay vì dùng một giá trị tĩnh cố định.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Ngọ Doãn Ngọc
