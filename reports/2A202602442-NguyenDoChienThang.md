# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Đỗ Chiến Thắng
- Mã học viên: 2A202602442
- Nhóm: BungChay
- Repository/branch: main

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Integration & UI | Tích hợp luồng RAG pipeline `generate_with_citation` vào giao diện Streamlit, thiết kế hiển thị câu trả lời kèm citation `[Document X]`, expander danh sách nguồn, score và phương thức truy xuất | `app.py` | Done |
| Benchmark Golden Dataset | Xây dựng bộ dữ liệu benchmark chuẩn gồm 16 cặp Q&A grounded trên cả 2 nguồn tài liệu pháp lý (Thông báo 106, Thông báo 52) và tin tức dịch vụ TVTT | `group_project/evaluation/golden_dataset.json` | Done |
| A/B Testing & Evaluation Report | Đo đạc và đối sánh 4 metrics (Faithfulness, Relevance, Recall, Precision) giữa Config A (Dense-only) và Config B (Hybrid + RRF); phân tích 3 ca lỗi worst performers và đề xuất giải pháp | `group_project/evaluation/RESULT.md` | Done |
| Testing & Contract Verification | Kiểm thử toàn diện toàn bộ 15 bài test contracts và 5 bài test acceptance, đảm bảo đạt 100% PASSED | `tests/test_contracts.py`, `tests/test_acceptance.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Sử dụng Reciprocal Rank Fusion (RRF, k=60) kết hợp Dense Semantic Search và BM25 Lexical Search.  
   **Lý do/evidence:** Tài liệu quy chế và biểu phí thư viện chứa nhiều số hiệu văn bản (TB 106, TB 52), con số biểu phí (45.000đ, 1.000.000đ) và mốc thời hạn (21 ngày, 30 ngày). BM25 giúp bắt trúng các thực thể từ khóa chính xác mà Dense search dễ bỏ sót, giúp nâng Context Recall từ 0.78 lên 0.93 (+0.15) và Context Precision từ 0.74 lên 0.89 (+0.15).  
   **Trade-off:** Độ trễ tìm kiếm tăng thêm khoảng 25-35ms do bước tokenize và tính điểm RRF, nhưng không làm phát sinh chi phí API và hoàn toàn nằm trong giới hạn tương tác người dùng chấp nhận được.

2. **Quyết định:** Thiết lập cơ chế Safe Refusal với ngưỡng Fallback Cosine Similarity 0.3.  
   **Lý do/evidence:** Tránh hiện tượng ảo giác (hallucination) của LLM khi gặp các câu hỏi ngoài phạm vi dữ liệu hoặc câu hỏi không có cơ sở dữ liệu xác thực, bảo vệ độ tin cậy của thông tin công bố từ nhà trường.  
   **Trade-off:** Đòi hỏi câu hỏi của người dùng phải có mức độ liên quan ngữ nghĩa đủ cao với tài liệu; nếu người dùng dùng từ quá khác biệt mà chưa có query expansion thì có thể bị từ chối trả lời an toàn.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: Bộ 16 câu hỏi Q&A kiểm thử grounded trong `golden_dataset.json` cùng bộ test tự động trong thư mục `tests/`.
- Kết quả trước/sau: Config B (Hybrid + RRF) đạt điểm trung bình 0.9200 (vượt trội so với 0.8125 của Config A Dense-only). Faithfulness đạt 0.94 nhờ thứ hạng context được cải thiện.
- Lỗi đã phát hiện và cách xử lý: Phát hiện bảng tiền thế chân trong tài liệu Thông báo 52 dễ bị cắt đôi qua ranh giới chunk, đã đề xuất cải tiến chunking giữ nguyên vẹn cấu trúc Markdown table.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Bộ từ khóa tìm kiếm BM25 chưa có từ điển đồng nghĩa tự động cho các từ viết tắt chuyên ngành trường học (như TVTT, ĐHQG-HCM, KTXB).
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Bổ sung lớp Query Expansion / Synonym Mapping để tự động chuẩn hóa câu hỏi người dùng trước khi đưa vào bước Hybrid Search.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Đỗ Chiến Thắng

