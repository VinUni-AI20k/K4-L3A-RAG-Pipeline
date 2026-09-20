# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Vũ Anh
- Mã học viên: 2A202602502
- Nhóm: K4-L3A
- Repository/branch: K4-L3A-RAG-Pipeline / vuanh

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| PageIndex Fallback & Retrieval Pipeline (Task 8 & 9) | Hoàn thiện Task 8 theo yêu cầu 2: hiện thực tự động upload tài liệu (convert Markdown sang PDF tạm bằng fpdf2), lưu cache document ID (`pageindex_doc_ids.json`) chống upload lặp, cơ chế timeout khi polling kết quả và parsing `retrieved_nodes` thành `SearchResult` chuẩn contract; tích hợp xử lý lỗi dịch vụ PageIndex tại Pipeline (Task 9) để fallback an toàn sang hybrid results thay vì crash | `src/task8_pageindex_vectorless.py`, `src/task9_retrieval_pipeline.py` | Done |
| Generation & Citation (Task 10) | Triển khai kỹ thuật Document Reordering chống lost-in-the-middle, định dạng context có gắn thẻ nguồn, dispatch LLM gọi Gemini streaming siêu tốc và cơ chế Safe Refusal | `src/task10_generation.py` | Done |
| Chatbot UI (app.py) | Xây dựng giao diện web chat tương tác bằng Streamlit theo phong cách hiện đại, hiển thị câu trả lời kèm citation, nguồn tài liệu tham khảo, retrieval method và score theo thời gian thực | `app.py` | Done |
| Architecture & Integration | Quản lý kiến trúc hệ thống, cấu hình môi trường (.env), điều phối kiểm thử toàn dự án và hoàn thiện Báo cáo đóng góp cá nhân | `src/`, `reports/2A202602502-NguyenVuAnh.md` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Thiết kế cơ chế Fallback PageIndex vectorless tích hợp cache `doc_id` và cô lập xử lý lỗi dịch vụ ngoại vi tại Pipeline.  
   **Lý do/evidence:** PageIndex là dịch vụ ngoài xử lý truy xuất logic theo cấu trúc cây (tree-based vectorless RAG). Do API là dịch vụ ngoài hoạt động bất đồng bộ (`submit_query` -> polling `get_retrieval`), việc cache `doc_id` vào `pageindex_doc_ids.json` giúp tái sử dụng ID và loại bỏ hoàn toàn chi phí upload trùng lặp. Đồng thời, việc thiết lập timeout (`PAGEINDEX_TIMEOUT = 30s`) và xử lý ngoại lệ an toàn tại `retrieve()` trong `src/task9_retrieval_pipeline.py` đảm bảo dù PageIndex có gặp sự cố (mạng, quá hạn, timeout), pipeline vẫn an toàn trả về kết quả Hybrid thay vì làm crash hệ thống.  
   **Trade-off:** Cần quản lý file cache và bước trung gian chuyển đổi Markdown sang PDF tạm, nhưng đổi lại hệ thống đạt độ chịu lỗi cao (fault-tolerant / graceful degradation) và vận hành ổn định.

2. **Quyết định:** Sử dụng điểm Cosine Similarity gốc của Dense Search làm điều kiện kích hoạt Fallback thay vì dùng điểm RRF.  
   **Lý do/evidence:** Điểm RRF chỉ phản ánh thứ hạng tương đối giữa các phần tử sau khi hợp nhất danh sách, không đại diện cho độ tin cậy tuyệt đối về mặt ngữ nghĩa. Do đó, việc so sánh `best_dense_score < score_threshold (0.3)` là căn cứ chuẩn xác nhất để nhận biết truy vấn nằm ngoài vùng ngữ nghĩa của Dense Search và cần kích hoạt cơ chế Fallback PageIndex.  
   **Trade-off:** Cần lưu vết điểm cosine gốc từ kết quả của Task 5 truyền qua Task 9, nhưng giúp pipeline đưa ra quyết định chuyển hướng chính xác và đúng bản chất.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: `pytest tests/test_contracts.py` (đặc biệt là các bài test `test_retrieve_uses_dense_score_for_fallback`, `test_retrieve_fuses_once_when_dense_is_confident`, `test_retrieve_survives_fallback_provider_error`) và kiểm thử logic `upload_documents`, `pageindex_search`.
- Kết quả trước/sau nếu có:
  - Trước: Task 8 để trống (`NotImplementedError`), không có cache khiến mỗi lần chạy có thể phải upload lại tốn tài nguyên, không có timeout kiểm soát polling, và nếu dịch vụ ngoài gặp sự cố thì pipeline bị crash.
  - Sau: Hoàn thiện trọn vẹn Task 8 với upload tự động, cache `doc_id` cục bộ, timeout 30s, parsing node chuẩn contract `SearchResult` (score giảm dần theo rank, id duy nhất, metadata đầy đủ). Pipeline xử lý ngoại lệ an toàn và đáp ứng hoàn hảo các bài test contract về Fallback và RRF.
- Lỗi đã phát hiện và cách xử lý:
  - PageIndex SDK yêu cầu định dạng PDF trong khi dữ liệu chuẩn hóa của repo là Markdown: đã giải quyết bằng cách bổ sung hàm chuyển đổi tự động `convert_markdown_to_pdf` với thư viện `fpdf2`, cấu hình font Unicode hệ thống (Arial) để bảo toàn tiếng Việt có dấu.
  - PageIndex API có thể bị chậm, nghẽn mạng hoặc lỗi dịch vụ: đã xử lý bằng timeout trong vòng lặp polling ở Task 8 và khối `try...except` tại hàm `retrieve()` ở Task 9, tự động chuyển tiếp sang kết quả hybrid và ghi log cảnh báo thay vì làm đứt đoạn pipeline.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Thời gian phản hồi của PageIndex phụ thuộc vào tốc độ mạng và hàng đợi xử lý bất đồng bộ từ máy chủ bên ngoài, có thể làm tăng độ trễ (latency) khi fallback được kích hoạt.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Bổ sung cơ chế gọi bất đồng bộ (`asyncio` hoặc nền tảng background worker) để submit query và thăm dò trạng thái kết quả song song, giảm thiểu độ trễ cho người dùng cuối.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Vũ Anh
