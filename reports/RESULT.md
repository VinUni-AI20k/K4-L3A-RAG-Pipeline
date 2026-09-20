# Kết quả đánh giá RAG

## Thông tin lần chạy

| Trường | Giá trị |
| ------ | ------- |
| Ngày đánh giá | 2026-09-20 |
| Framework và phiên bản | pytest 9.1.1; OpenAI evaluator qua `openai` SDK |
| Mô hình chấm điểm | gpt-4o-mini |
| Mô hình sinh câu trả lời | gpt-4o-mini |
| Mô hình embedding | HashingVectorizer 1024 chiều cho lần chạy local này |
| Phiên bản corpus/commit | Corpus local trong `data/landing` và `data/standardized` |
| Kích thước golden dataset | 15 câu |
| `top_k` | 5 |
| Ngưỡng fallback và hiệu chỉnh | 0.3; dùng mặc định của pipeline |

## Cấu hình thử nghiệm

- **Cấu hình A - dense-only:** `retrieve(..., use_reranking=False)` trả kết quả dense từ ChromaDB.
- **Cấu hình B - hybrid + RRF:** `retrieve(..., use_reranking=True)` gộp dense và BM25 bằng Reciprocal Rank Fusion.

Hai cấu hình dùng cùng corpus, golden dataset, prompt, evaluator model và `top_k`; chỉ thay chiến lược retrieval.

## Điểm tổng quan (overall scores)

| Metric | Cấu hình A | Cấu hình B | Chênh lệch B-A |
| ------ | ---------: | ---------: | --------------: |
| Faithfulness | 0.69 | 0.79 | 0.10 |
| Answer relevance | 0.75 | 0.83 | 0.08 |
| Context recall | 0.79 | 0.78 | -0.01 |
| Context precision | 0.50 | 0.54 | 0.04 |
| **Trung bình** | 0.69 | 0.74 | 0.05 |

Điểm được chấm bằng LLM-as-judge trên 15 câu trong golden dataset. Đây là kết quả thực nghiệm local, phụ thuộc vào corpus hiện tại và embedding hashing đang dùng để tránh tải model lớn.

## So sánh A/B (a/b comparison)

- Cấu hình tốt hơn: Config B - hybrid + RRF.
- Bằng chứng: Điểm trung bình dense-only = 0.69, hybrid + RRF = 0.74. Hybrid cao hơn 0.05.
- Đánh đổi về độ trễ/chi phí: Hybrid gọi cả dense search và BM25 nên chậm hơn dense-only một chút, nhưng không làm tăng số lần gọi LLM trong pha generation/evaluation.

## Các ca kém nhất (worst performers)

| # | Câu hỏi | Cấu hình | Faithfulness | Relevance | Recall | Precision | Giai đoạn lỗi | Nguyên nhân gốc |
| -: | ------- | -------- | -----------: | --------: | -----: | --------: | ------------- | --------------- |
| 1 | Nếu hỏi về điểm chuẩn PTIT 2026 thì nên dùng nguồn nào? | Dense-only | 0.00 | 0.00 | 0.00 | 0.00 | answer generation | Câu trả lời không dựa trên thông tin từ retrieved contexts và không trả lời đúng câu hỏi. |
| 2 | Corpus có bao nhiêu tài liệu legal PDF gốc? | Hybrid + RRF | 0.00 | 0.00 | 0.50 | 0.20 | answer generation | Câu trả lời không chính xác và không dựa trên thông tin từ các retrieved contexts. |
| 3 | Nếu câu hỏi ngoài phạm vi corpus, chatbot nên làm gì? | Hybrid + RRF | 0.50 | 1.00 | 0.00 | 0.00 | context_recall | Retrieved contexts do not contain relevant information to answer the question. |

## Khuyến nghị (recommendations)

| Ưu tiên | Hành động | Bằng chứng từ phân tích lỗi | Tác động kỳ vọng | Cách kiểm chứng |
| ------: | --------- | --------------------------- | ---------------- | --------------- |
| 1 | OCR hoặc thay PDF scan bằng PDF có text layer | Legal Markdown fallback chưa chứa nội dung chi tiết | Tăng context recall cho câu hỏi legal | Chạy lại Task 3 và kiểm tra legal Markdown có nội dung thật |
| 2 | Dùng embedding semantic thật như BAAI/bge-m3 hoặc OpenAI embeddings | Lần chạy local dùng hashing để tránh tải model lớn | Tăng chất lượng dense retrieval | Re-index ChromaDB và chạy lại bảng điểm này |
| 3 | Hiệu chỉnh `SCORE_THRESHOLD` | Ngưỡng 0.3 là mặc định template | Fallback hợp lý hơn cho câu hỏi ngoài domain | So sánh query đúng miền và ngoài miền |

## Thử nghiệm bonus

| Thử nghiệm | Baseline | Chênh lệch metric | Chênh lệch độ trễ/chi phí | Kết luận |
| ---------- | -------- | ----------------: | ------------------------: | -------- |
| Query expansion | Hybrid + RRF | Chưa chạy | Chưa chạy | Chưa đánh giá |
| Reranker nâng cao | RRF | Chưa chạy | Chưa chạy | Chưa đánh giá |
| Conversation memory | Chat một lượt | Chưa chạy | Chưa chạy | Chưa đánh giá |
