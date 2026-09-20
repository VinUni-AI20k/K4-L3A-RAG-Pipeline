# RAG evaluation results

## Run information

| Field | Value |
| ------ | ------- |
| Evaluation date | 2026-09-20 |
| Framework and version | pytest 9.1.1; đánh giá LLM-as-judge bằng gpt-4o-mini |
| Evaluator model | gpt-4o-mini |
| Generator model | gpt-4o-mini |
| Embedding model | HashingVectorizer 1024 chiều (chạy local) |
| Corpus version/commit | 3 file PDF (đã OCR bằng Gemini) và 5 bài báo về tuyển sinh PTIT |
| Golden dataset size | 15 câu Q&A |
| `top_k` | 5 |
| Fallback threshold and calibration | 0.3 |

## Configurations

- **Config A — dense-only:** Tìm kiếm bằng vector cosine trên ChromaDB.
- **Config B — hybrid + RRF:** Kết hợp Dense search và BM25 (lexical), gộp kết quả bằng Reciprocal Rank Fusion (k=60).

*Hai cấu hình dùng chung prompt, dataset và LLM, chỉ khác phương pháp truy xuất.*

## Overall scores

| Metric | Config A | Config B | Delta B-A |
| ------ | ---------: | ---------: | --------------: |
| Faithfulness | 0.69 | 0.79 | +0.10 |
| Answer relevance | 0.75 | 0.83 | +0.08 |
| Context recall | 0.79 | 0.78 | -0.01 |
| Context precision | 0.50 | 0.54 | +0.04 |
| **Trung bình** | 0.69 | 0.74 | +0.05 |

## A/B comparison

- **Better configuration:** Cấu hình B (Hybrid + RRF) tốt hơn rõ rệt. 
- **Evidence:** Các câu hỏi về tuyển sinh PTIT có nhiều mã ngành, con số học phí cụ thể (ví dụ "7320104", "23 triệu"). Dense search thuần túy bắt các từ khóa này không tốt bằng BM25. Khi gộp bằng RRF, ta lấy được ưu điểm của cả hai, giúp chatbot trả lời chính xác số liệu hơn.
- **Latency/cost trade-off:** Cấu hình B tốn thời gian chạy BM25 trên toàn bộ chunks nên chậm hơn một chút, nhưng chưa đáng kể vì bộ dữ liệu hiện tại còn mỏng.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| -: | ------- | -------- | -----------: | --------: | -----: | --------: | ------------- | --------------- |
| 1 | Nếu hỏi về điểm chuẩn PTIT 2026 thì nên dùng nguồn nào? | Dense-only | 0.00 | 0.00 | 0.00 | 0.00 | Retrieval | Vector search không lấy được metadata của file PDF, nó tìm nội dung bên trong file thay vì tìm tên file, dẫn đến chatbot không biết chỉ ra nguồn nào. |
| 2 | Corpus có bao nhiêu tài liệu legal PDF gốc? | Hybrid | 0.00 | 0.00 | 0.50 | 0.20 | Retrieval | RAG đọc nội dung chữ (chunks), không đọc được cấu trúc thư mục ổ cứng nên không thể đếm số lượng file PDF. Câu này nằm ngoài khả năng của bộ RAG hiện tại. |
| 3 | Nếu câu hỏi ngoài phạm vi corpus, chatbot nên làm gì? | Hybrid | 0.50 | 1.00 | 0.00 | 0.00 | Retrieval | System prompt định nghĩa luật từ chối nằm trong code hệ thống chứ không nằm trong tài liệu cơ sở dữ liệu. Retriever tìm không thấy nên recall = 0, nhưng LLM vẫn hiểu và tự sinh câu trả lời hợp lý. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| ------: | --------- | --------------------------- | --------------- |
| 1 | Đổi mô hình embedding | Hiện tại nhóm đang giả lập embedding bằng HashingVectorizer do chạy trên máy lab không có GPU, dẫn đến điểm Context Precision thấp (0.50). | Tăng khả năng truy xuất đúng đoạn chứa số liệu và metadata quan trọng. | Chuyển sang OpenAI text-embedding-3-small, index lại database và chạy lại bộ test 15 câu để so điểm. |
| 2 | Tăng dữ liệu crawl | Bộ dữ liệu chỉ có 5 bài news và 3 file PDF, hơi nghèo nàn để chatbot trả lời đa dạng các tình huống. | Tăng độ phủ thông tin để giảm các câu trả lời thiếu căn cứ. | Viết code crawl đệ quy thêm 20-30 bài trên trang tuyển sinh PTIT. |
| 3 | Tích hợp Agentic Tools | Chatbot hiện bó tay với các câu hỏi đếm số lượng (kiểu "có bao nhiêu bài viết"). | Trả lời được câu hỏi cần thao tác hệ thống thay vì chỉ dựa vào vector search. | Tích hợp thêm function calling (tool) để code python đếm file thực tế thay vì đi tìm kiếm vector. |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | ------------ | ------------------ | ---------- |
| Chưa chạy thí nghiệm bổ sung | Config B — hybrid + RRF | Chưa có số liệu mới | Chưa có số liệu mới | Giữ làm hướng mở rộng sau khi thay embedding thật và tăng corpus. |

## Bảng phân công thực hiện

| Thành viên | Việc trực tiếp code / đóng góp trong file dự án |
| -------------------- | ------ |
| Ngụy Quang Hùng (Task 1, 7) | Tải 3 file PDF pháp lý thủ công để đảm bảo file gốc. Cài đặt thuật toán RRF gộp danh sách hạng BM25 và Dense. |
| Nguyễn Văn Việt (Task 2, 8) | Code tool crawl bài viết tự động bằng Crawl4AI. Viết hàm gọi external API PageIndex và xử lý lỗi fallback để code không bị văng. |
| Đinh Xuân Quyền (Task 4, 5, 6) | Viết code băm tài liệu thành chunks (chia đoạn), mã hóa vector và nạp vào cơ sở dữ liệu ChromaDB. Code 2 hàm truy vấn Dense và BM25. |
| Hà Huy Nhất (Task 3, 9, 10) | Viết kịch bản OCR bằng Gemini Vision để lấy chữ từ file scan đóng dấu đỏ. Gắn ghép luồng RAG hoàn chỉnh (ngưỡng fallback, prompt từ chối an toàn) và đánh giá A/B. |
