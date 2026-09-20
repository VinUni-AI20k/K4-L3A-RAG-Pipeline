# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | Ragas 0.4.3 / Custom Evaluation Pipeline |
| Evaluator model                    | gpt-4o-mini (OpenAI) / Gemini-1.5-Flash |
| Generator model                    | gpt-4o-mini |
| Embedding model                    | BAAI/bge-m3 (1024-dim) via SentenceTransformers |
| Corpus version/commit              | commit 0c44996f (VNU-UET Regulations & Student Services) |
| Golden dataset size                | 16 ground-truth Q&A pairs (10 Legal + 6 News) |
| `top_k`                            | 5 |
| Fallback threshold and calibration | 0.35 (calibrated on in-domain VNU vs out-of-domain queries) |

## Configurations

- **Config A — dense-only:** Chỉ sử dụng vector semantic search thông qua ChromaDB (`cosine distance`, score = `max(0, 1 - distance)`).
- **Config B — hybrid + RRF:** Kết hợp dense semantic search và BM25 lexical search bằng Reciprocal Rank Fusion (RRF với $k=60$).

Hai config phải dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      |     0.82 |     0.94 |     +0.12 |
| Answer relevance  |     0.78 |     0.91 |     +0.13 |
| Context recall    |     0.69 |     0.88 |     +0.19 |
| Context precision |     0.65 |     0.85 |     +0.20 |
| **Average**       | **0.735**| **0.895**| **+0.160**|

## A/B comparison

- Cấu hình tốt hơn: **Config B (Hybrid + RRF)** vượt trội hoàn toàn so với Config A trên cả 4 thước đo đánh giá.
- Evidence: 
  - Context Recall tăng vọt từ 0.69 lên 0.88 (+19%) và Context Precision tăng từ 0.65 lên 0.85 (+20%). Điều này chứng minh BM25 đóng vai trò then chốt trong việc bắt chính xác các từ khóa thực thể đặc thù (mã quyết định "QĐ 3626", địa điểm "P.107-G2", mốc thời gian "21/01/2026", tỷ lệ học phí "120.000.000 VNĐ"), những điểm mà dense retrieval thuần túy thường làm mờ nhạt vector biểu diễn.
  - Faithfulness tăng từ 0.82 lên 0.94 nhờ context đưa vào LLM giàu sự thật liên quan trực tiếp hơn, giảm thiểu hiện tượng hallucination ở generator.
- Trade-off về latency/cost: 
  - Latency của Config B (108.1ms) cao hơn Config A (66.9ms) xấp xỉ 41.2ms (+61%) do phải thực hiện thêm 1 lượt BM25 scoring trên toàn bộ 472 chunks và tính toán thuật toán RRF. 
  - Tuy nhiên mức latency ~108ms vẫn nằm hoàn toàn trong ngưỡng phản hồi thời gian thực chấp nhận được (<200ms) của hệ thống chatbot tương tác. Về mặt API cost, cả hai config tiêu tốn cùng số token input/output cho LLM do cùng cố định `top_k = 5`.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage             | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------------------- | ---------- |
|   1 | Thang điểm chữ A+, A, B+ quy đổi sang thang điểm 4 tương ứng với bao nhiêu điểm? | Config A | 0.60 | 0.70 | 0.40 | 0.35 | retrieval | Bảng quy đổi điểm dạng ký tự viết tắt ngắn ("A+", "B+", "3.7") bị loãng ngữ nghĩa khi chunking 500 ký tự, khiến dense vector embedding không khớp tốt với câu hỏi dạng danh sách số học. |
|   2 | Sinh viên tốt nghiệp đợt tháng 01/2026 tại UET nộp ảnh làm bằng tốt nghiệp ở đâu và hạn chót khi nào? | Config A | 0.70 | 0.75 | 0.50 | 0.45 | retrieval | Truy vấn chứa các thực thể hành chính địa phương ("P.107-G2", "ảnh 3x4", "21/01/2026"); dense model bắt ngữ nghĩa chung chung về tốt nghiệp thay vì thông báo nộp ảnh cụ thể của phòng CTSV. |
|   3 | Sinh viên UET đăng ký tham gia cuộc thi Học sinh, sinh viên với ý tưởng khởi nghiệp trước ngày nào và nộp những sản phẩm gì? | Config B | 0.85 | 0.80 | 0.70 | 0.60 | generation | Văn bản gốc chứa cụm từ "Bản thuyết minh dự án" và "Video clip thuyết minh", generator đôi khi tóm tắt quá gọn khiến câu trả lời thiếu chi tiết phụ lục mẫu. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Bổ sung Table/Markdown-aware chunking chuyên dụng cho các bảng quy chế (thang điểm, định mức học bổng) | Trường hợp thất bại #1 cho thấy chunking ngắt quãng theo số ký tự (500 chars) làm vỡ cấu trúc ma trận cột của bảng điểm Điều 41. | Tăng Context Recall cho các câu hỏi tra cứu bảng biểu từ 0.70 lên >0.95. | Chạy lại eval trên các câu hỏi liên quan đến bảng điểm và khung học bổng. |
|        2 | Tinh chỉnh trọng số RRF và tăng candidate pool trước khi rerank (ví dụ: top 20 dense + top 20 BM25 gộp thành top 5) | Trong các câu hỏi thực thể ngày tháng (Worst performer #2), BM25 đưa văn bản chính xác vào rank 6-7 nên bị cắt mất khi chỉ lấy candidate pool nhỏ. | Giúp tăng Recall các thực thể tin tức lên 100%. | So sánh tỷ lệ Top-k retrieval hit với các ngưỡng candidate pool khác nhau. |
|        3 | Cải thiện System Prompt phân cấp rõ: Quy định khung (ĐHQGHN) vs Triển khai thực thi (UET) | Tránh việc LLM bị bối rối khi sinh viên hỏi địa điểm nộp hồ sơ cấp trường so với thẩm quyền cấp ĐHQGHN. | Tăng Answer Relevance và độ chuẩn xác của Citation từ 0.91 lên >0.98. | Kiểm tra thủ công tính chuẩn xác của trích dẫn nguồn văn bản (Legal vs News). |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Candidate Pool Expansion (Top 20 -> RRF -> Top 5) | Baseline Hybrid Top 10 | Context Recall: +0.06 (0.88 -> 0.94) | Latency: +14.2ms | Tăng vùng phủ ứng viên trước khi gộp RRF giúp cứu được các chunk chứa thông tin bảng điểm bị tụt hạng. |
| Query Expansion với từ đồng nghĩa học vụ tiếng Việt ("ĐRL", "GPA", "CTSV") | Baseline BM25 đơn thuần | Answer Relevance: +0.05 (0.91 -> 0.96) | Latency: +8.5ms | Cải thiện đáng kể khả năng tìm kiếm của BM25 với các thuật ngữ viết tắt sinh viên thường dùng. |
