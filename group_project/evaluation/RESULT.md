# Kết quả đánh giá RAG

## Thông tin lần chạy

| Trường | Giá trị |
| ------ | ------- |
| Ngày đánh giá | 2026-09-20 |
| Framework và phiên bản | pytest 9.1.1; đánh giá LLM-as-judge bằng gpt-4o-mini |
| Mô hình sinh câu trả lời | gpt-4o-mini |
| Mô hình embedding | HashingVectorizer 1024 chiều (chạy local) |
| Phiên bản corpus | 3 file PDF (đã OCR bằng Gemini) và 5 bài báo về tuyển sinh PTIT |
| Kích thước golden dataset | 15 câu Q&A |
| `top_k` | 5 |
| Ngưỡng fallback | 0.3 |

## Cấu hình thử nghiệm

- **Cấu hình A (Chỉ dùng Dense):** Tìm kiếm bằng vector cosine trên ChromaDB.
- **Cấu hình B (Hybrid + RRF):** Kết hợp Dense search và BM25 (lexical), gộp kết quả bằng Reciprocal Rank Fusion (k=60).

*Hai cấu hình dùng chung prompt, dataset và LLM, chỉ khác phương pháp truy xuất.*

## Điểm tổng quan (overall scores)

| Metric | Cấu hình A | Cấu hình B | Chênh lệch (B-A) |
| ------ | ---------: | ---------: | --------------: |
| Faithfulness | 0.69 | 0.79 | +0.10 |
| Answer relevance | 0.75 | 0.83 | +0.08 |
| Context recall | 0.79 | 0.78 | -0.01 |
| Context precision | 0.50 | 0.54 | +0.04 |
| **Trung bình** | 0.69 | 0.74 | +0.05 |

## Phân tích so sánh A/B (a/b comparison)

- **Kết luận:** Cấu hình B (Hybrid + RRF) tốt hơn rõ rệt. 
- **Lý do thực tế:** Các câu hỏi về tuyển sinh PTIT có nhiều mã ngành, con số học phí cụ thể (ví dụ "7320104", "23 triệu"). Dense search thuần túy bắt các từ khóa này không tốt bằng BM25. Khi gộp bằng RRF, ta lấy được ưu điểm của cả hai, giúp chatbot trả lời chính xác số liệu hơn.
- **Đánh đổi:** Cấu hình B tốn thời gian chạy BM25 trên toàn bộ chunks nên chậm hơn một chút, nhưng chưa đáng kể vì bộ dữ liệu hiện tại còn mỏng.

## Các ca kém nhất (worst performers)

| # | Câu hỏi | Cấu hình | Faithfulness | Relevance | Recall | Precision | Lỗi ở đâu? | Giải thích thực tế |
| -: | ------- | -------- | -----------: | --------: | -----: | --------: | ------------- | --------------- |
| 1 | Nếu hỏi về điểm chuẩn PTIT 2026 thì nên dùng nguồn nào? | Dense-only | 0.00 | 0.00 | 0.00 | 0.00 | Retrieval | Vector search không lấy được metadata của file PDF, nó tìm nội dung bên trong file thay vì tìm tên file, dẫn đến chatbot không biết chỉ ra nguồn nào. |
| 2 | Corpus có bao nhiêu tài liệu legal PDF gốc? | Hybrid | 0.00 | 0.00 | 0.50 | 0.20 | Retrieval | RAG đọc nội dung chữ (chunks), không đọc được cấu trúc thư mục ổ cứng nên không thể đếm số lượng file PDF. Câu này nằm ngoài khả năng của bộ RAG hiện tại. |
| 3 | Nếu câu hỏi ngoài phạm vi corpus, chatbot nên làm gì? | Hybrid | 0.50 | 1.00 | 0.00 | 0.00 | Retrieval | System prompt định nghĩa luật từ chối nằm trong code hệ thống chứ không nằm trong tài liệu cơ sở dữ liệu. Retriever tìm không thấy nên recall = 0, nhưng LLM vẫn hiểu và tự sinh câu trả lời hợp lý. |

## Khuyến nghị cải tiến (recommendations)

| Ưu tiên | Việc cần làm | Lý do thực tế | Cách kiểm tra |
| ------: | --------- | --------------------------- | --------------- |
| 1 | Đổi mô hình embedding | Hiện tại nhóm đang giả lập embedding bằng HashingVectorizer do chạy trên máy lab không có GPU, dẫn đến điểm Context Precision thấp (0.50). | Chuyển sang OpenAI text-embedding-3-small, index lại database và chạy lại bộ test 15 câu để so điểm. |
| 2 | Tăng dữ liệu crawl | Bộ dữ liệu chỉ có 5 bài news và 3 file PDF, hơi nghèo nàn để chatbot trả lời đa dạng các tình huống. | Viết code crawl đệ quy thêm 20-30 bài trên trang tuyển sinh PTIT. |
| 3 | Tích hợp Agentic Tools | Chatbot hiện bó tay với các câu hỏi đếm số lượng (kiểu "có bao nhiêu bài viết"). | Tích hợp thêm function calling (tool) để code python đếm file thực tế thay vì đi tìm kiếm vector. |

## Bảng phân công thực hiện

| Thành viên | Việc trực tiếp code / đóng góp trong file dự án |
| -------------------- | ------ |
| Ngụy Quang Hùng (Task 1, 7) | Tải 3 file PDF pháp lý thủ công để đảm bảo file gốc. Cài đặt thuật toán RRF gộp danh sách hạng BM25 và Dense. |
| Nguyễn Văn Việt (Task 2, 8) | Code tool crawl bài viết tự động bằng Crawl4AI. Viết hàm gọi external API PageIndex và xử lý lỗi fallback để code không bị văng. |
| Đinh Xuân Quyền (Task 4, 5, 6) | Viết code băm tài liệu thành chunks (chia đoạn), mã hóa vector và nạp vào cơ sở dữ liệu ChromaDB. Code 2 hàm truy vấn Dense và BM25. |
| Hà Huy Nhất (Task 3, 9, 10) | Viết kịch bản OCR bằng Gemini Vision để lấy chữ từ file scan đóng dấu đỏ. Gắn ghép luồng RAG hoàn chỉnh (ngưỡng fallback, prompt từ chối an toàn) và đánh giá A/B. |
