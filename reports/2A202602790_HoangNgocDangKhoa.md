# Individual contribution report

## Thông tin

- Họ và tên: Hoàng Ngọc Đăng Khoa
- Mã học viên: 2A202602790
- Lớp: K4-L3A
- Nhóm: Phronesis
- Repository/branch: https://github.com/nthanhwork/K4-L3A-RAG-Pipeline / branch: main

---

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| **Golden Dataset Verification & Acceptance** | Tiếp nhận, kiểm tra và nghiệm thu bộ dữ liệu chuẩn gồm 16 cặp câu hỏi - câu trả lời - context trích xuất từ 3 Nghị định pháp lý (357, 358, 359/2026) và 5 bài báo nghiệp vụ. Đảm bảo 100% ca kiểm thử có căn cứ ngữ cảnh xác thực, phân bổ đều giữa các dạng câu hỏi tra cứu thông tin, số liệu định lượng, điều kiện hỗ trợ và quy trình nộp ngân sách. Vượt qua bài kiểm tra `test_golden_dataset_has_15_grounded_cases`. | `group_project/evaluation/golden_dataset.json` | Done |
| **A/B Benchmark & 4 Metrics Evaluation** | Vận hành script đo lường tự động `run_eval.py`, tiến hành đo đạc và tính toán 4 metrics cốt lõi của RAG (Faithfulness, Answer Relevance, Context Recall, Context Precision) trên cả 2 cấu hình Config A (Dense-only) và Config B (Hybrid + RRF). Thu thập dữ liệu thực nghiệm so sánh phương sai (Delta B - A). | `group_project/evaluation/run_eval.py`, `group_project/evaluation/RESULT.md` | Done |
| **Failure Analysis (Phân tích lỗi Worst Performers)** | Phân tích sâu 3 trường hợp có điểm số thấp nhất trong bài benchmark, phân loại chính xác nguồn gốc lỗi theo từng giai đoạn (Retrieval, Generation, Data) và chỉ ra nguyên nhân gốc rễ (phân tán từ khóa 'cơ cấu lại vốn', loãng số liệu tỷ lệ trong vector, hiện tượng LLM tóm tắt thiếu ý). | `group_project/evaluation/RESULT.md`, `reports/RESULT.md` | Done |
| **Đề xuất cải tiến kỹ thuật (Recommendations)** | Xây dựng 3 khuyến nghị ưu tiên theo thứ tự tác động: Bổ sung Metadata Filtering theo nguồn văn bản pháp luật, chuyển đổi sang Semantic/Section Chunking theo điều khoản, và tối ưu Prompt ép trích dẫn toàn diện danh sách điểm mới. Đánh giá 2 thử nghiệm mở rộng (+4 điểm Bonus: Conversation Memory & Citation Highlighting). | `group_project/evaluation/RESULT.md` | Done |
| **Kiểm thử nghiệm thu toàn hệ thống** | Chạy và xác thực toàn bộ bộ kiểm thử của dự án, đạt kết quả tuyệt đối **20/20 test pass** (15 contract tests trong `tests/test_contracts.py` và 5 acceptance tests trong `tests/test_acceptance.py`). | `tests/test_contracts.py`, `tests/test_acceptance.py` | Done |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định: Lựa chọn chiến lược đánh giá phân tầng (Stratified Evaluation) kết hợp giữa RAG Triad và Context Metrics để bóc tách độc lập hiệu năng của khâu Retrieval và Generation.**  
   - **Lý do/evidence:** Trong một pipeline RAG phức tạp, nếu chỉ đánh giá end-to-end câu trả lời cuối cùng (Faithfulness & Answer Relevance), khi gặp câu trả lời kém chất lượng sẽ không thể xác định chính xác lỗi do bộ tìm kiếm không lấy được tài liệu liên quan hay do mô hình ngôn ngữ (LLM) bị ảo giác (hallucination). Bằng cách đo đạc độc lập Context Recall & Context Precision (đánh giá ChromaDB, BM25 và RRF) song song với Faithfulness & Answer Relevance (đánh giá LLM generator), nhóm đã chứng minh định lượng được rằng: Cấu hình Hybrid + RRF giúp tăng Context Precision từ **0.92 lên 0.97 (+0.05)**, từ đó kéo theo Answer Relevance tăng từ **0.91 lên 0.95 (+0.04)** và Faithfulness đạt **0.96 (+0.03)**.
   - **Trade-off:** Đòi hỏi khâu chuẩn bị Golden Dataset phải công phu hơn (bắt buộc phải trích xuất expected_context nguyên văn thay vì chỉ viết câu trả lời mẫu), nhưng mang lại khả năng chẩn đoán lỗi chính xác cho từng thành viên phụ trách các module riêng biệt.

2. **Quyết định: Thiết lập quy trình phân tích nguyên nhân gốc rễ (Root Cause Analysis) cho từng ca thất bại (Worst Performers) thay vì chỉ nhìn vào điểm số trung bình.**  
   - **Lý do/evidence:** Điểm trung bình tổng thể của hệ thống khá cao (0.9225), điều này dễ tạo ra cảm giác an tâm giả tạo và bỏ qua các lỗi nghiêm trọng trong nghiệp vụ tra cứu văn bản pháp luật. Khi đi sâu vào 3 trường hợp điểm thấp nhất, tôi đã phân loại rõ:
     - Câu 1: Lỗi ở khâu **Retrieval** do cụm từ 'cơ cấu lại vốn' lặp lại quá nhiều trong Nghị định 357 khiến Dense search bị nhiễu giữa các điều khoản chi thường xuyên và chi đầu tư.
     - Câu 2: Lỗi ở khâu **Retrieval** do các số liệu tỷ lệ phần trăm (118%, 117%, 200%, 5,6 lần) bị loãng trong không gian vector dày đặc; Config B với BM25 đã khắc phục thành công nhờ khớp chính xác token số liệu.
     - Câu 3: Lỗi ở khâu **Generation** do câu hỏi yêu cầu tổng hợp đa ý khiến LLM tóm tắt lược bỏ bớt 1 điểm mới của Nghị định 358.
   - **Trade-off:** Tốn thời gian truy vết log từng lượt truy xuất và kiểm tra từng chunk văn bản, nhưng cung cấp cơ sở vững chắc để đưa ra các đề xuất cải tiến có tính khả thi cao (như Metadata Filtering và Semantic Chunking).

---

## Kiểm thử và kết quả

- **Các bài kiểm thử đã thực hiện:**
  - `pytest tests/test_contracts.py -q`: Đạt **15/15 passed** (toàn bộ hợp đồng dữ liệu, schema SearchResult, GenerationResult, `rerank_rrf`, `pageindex_search` đều chuẩn hóa).
  - `pytest tests/test_acceptance.py -q`: Đạt **5/5 passed** (đầy đủ tài liệu pháp luật, tin tức kèm metadata, markdown chuẩn hóa, 16 ca golden dataset và file RESULT.md hoàn thiện không còn TODO).
  - Toàn bộ test suite: `pytest -q` đạt **20/20 passed**.
- **Kết quả đo kiểm A/B trên 16 câu hỏi Golden Dataset:**
  - **Config A (Dense-only):** Faithfulness = 0.93, Answer Relevance = 0.91, Context Recall = 0.83, Context Precision = 0.92 | Điểm trung bình: **0.8975**.
  - **Config B (Hybrid + RRF):** Faithfulness = 0.96, Answer Relevance = 0.95, Context Recall = 0.81, Context Precision = 0.97 | Điểm trung bình: **0.9225**.
  - **Delta (B − A):** Context Precision tăng **+0.05**, Answer Relevance tăng **+0.04**, Faithfulness tăng **+0.03**. Kết luận: Cấu hình Hybrid kết hợp RRF vượt trội hơn hẳn về độ chính xác và tính xác thực trong nghiệp vụ tra cứu pháp lý.
- **Lỗi đã phát hiện và xử lý:**
  - Phát hiện trong quá trình chạy benchmark: Các câu hỏi chứa số hiệu văn bản (như 359/2026/NĐ-CP, Mẫu số 02/PTQ) nếu chỉ dùng Dense Search thuần túy rất dễ bị trôi sang các nghị định tương tự; xác nhận giải pháp kết hợp BM25 của Role Retrieval là hoàn toàn đúng đắn để ghim chặt các token thực thể chính xác.

---

## Điều còn hạn chế

- **Hạn chế cụ thể:** Bộ Golden Dataset hiện có quy mô 16 câu hỏi, tập trung chủ yếu vào các câu hỏi đơn lẻ (single-hop). Hệ thống chưa được đánh giá trên tập dữ liệu câu hỏi đa tầng phức tạp (multi-hop reasoning) liên kết đồng thời quy định giữa nhiều nghị định (ví dụ: liên kết quy định xử lý nợ giữa VAMC theo NĐ 359 và chuyển giao tài sản cho DATC theo NĐ 358).
- **Nếu có thêm thời gian:** Tôi sẽ mở rộng Golden Dataset lên 50+ câu hỏi sử dụng phương pháp tạo dữ liệu bán tự động (LLM-assisted synthesis có chuyên gia thẩm định), đồng thời bổ sung thêm các bộ câu hỏi bẫy (adversarial queries / out-of-domain) để kiểm tra ngưỡng ngắt an toàn (safe refusal rate) của hệ thống một cách triệt để hơn.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại toàn bộ quy trình đo kiểm trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Hoàng Ngọc Đăng Khoa
