# Individual contribution report

---

## Thông tin

- Họ và tên: Ngô Tiến Dũng
- Mã học viên: 2A202602374
- Nhóm: K4-L3A-RAG-Pipeline
- Repository/branch: K4-L3A-RAG-Pipeline (local workspace)

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm                                                         | File/commit/PR                                                                                   | Trạng thái |
| ------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ | ---------- |
| Data collection    | Thu thập và kiểm tra dữ liệu pháp lý và tin tức liên quan giao thông đường bộ  | `data/landing/legal`, `data/landing/news`                                                        | Done       |
| Standardization    | Chuẩn hóa tài liệu sang Markdown để dùng trong pipeline                        | `data/standardized/legal`, `data/standardized/news`                                              | Done       |
| Retrieval pipeline | Kiểm tra và đồng bộ hóa pipeline dense/BM25 + fallback                         | `src/task5_semantic_search.py`, `src/task6_lexical_search.py`, `src/task9_retrieval_pipeline.py` | Done       |
| Evaluation setup   | Tạo dataset golden, kiểm tra báo cáo đánh giá và đối chiếu với acceptance test | `group_project/evaluation/golden_dataset.json`, `group_project/evaluation/RESULT.md`             | Done       |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng hybrid retrieval (semantic + BM25) và RRF thay vì dense-only cho các câu hỏi pháp lý và tin tức giao thông.  
   **Lý do/evidence:** Khi so sánh A/B, Config B đạt điểm recall và precision cao hơn rõ rệt trên câu hỏi cần cả từ khóa và ngữ nghĩa.  
   **Trade-off:** Tăng nhẹ latency và chi phí xử lý, nhưng giảm lỗi khi truy xuất tài liệu có mốc pháp lý cụ thể.

2. **Quyết định:** Chuẩn hóa tài liệu sang Markdown trước khi chunk và index.  
   **Lý do/evidence:** Giúp pipeline đọc được nội dung ổn định, dễ tách chunks theo văn bản pháp lý và bài báo, giảm sai lệch khi nạp vào vector store.  
   **Trade-off:** Tốn thêm bước xử lý ban đầu, nhưng tăng độ nhất quán của dữ liệu và chất lượng retrieval.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: `pytest tests/test_acceptance.py -q`, kiểm tra các câu hỏi về luật giao thông, mức phạt, ưu tiên làn đường, và các tài liệu pháp lý.
- Kết quả trước/sau nếu có: Trước đây báo cáo và golden dataset còn placeholder, dẫn đến 2 fail. Sau khi hoàn thiện, kiểm thử đạt trạng thái pass.
- Lỗi đã phát hiện và cách xử lý: File JSON rỗng và file report còn `TODO`; tôi đã điền dữ liệu thực tế và chuẩn hóa định dạng để thỏa mãn test.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: hiệu năng retrieval hybrid vẫn có thể tăng thêm latency khi corpus lớn hơn.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: tối ưu chunking theo section và thêm query rewrite cho câu hỏi mơ hồ.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Ngô Tiến Dũng
