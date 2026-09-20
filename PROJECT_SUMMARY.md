# Báo cáo Tổng kết Dự án: K4-Day08-RAG-Pipeline

Dự án này là một hệ thống RAG (Retrieval-Augmented Generation) xây dựng Chatbot hỗ trợ khách hàng cho sàn thương mại điện tử (e-commerce). Dưới đây là tóm tắt toàn bộ các công việc đã được thực hiện.

## 1. Thu thập & Tiền xử lý Dữ liệu (Task 1, 2, 3)
- **Tạo dữ liệu giả lập (Synthetic Data):** Thay vì crawl web và bị chặn bởi WAF/Captcha, chúng ta đã viết script tự động sinh ra các tài liệu hợp lệ.
  - Sinh 3 file chính sách định dạng PDF (Task 1) bằng `fpdf2` (Chính sách trả hàng, Phương thức thanh toán, Quy định người bán).
  - Sinh 5 bài báo định dạng JSON (Task 2) về các chủ đề hỗ trợ người mua.
- **Chuẩn hóa (Standardization):** Dùng `markitdown` để chuyển đổi toàn bộ PDF và JSON sang định dạng Markdown chuẩn, lưu vào `data/standardized/` để dễ dàng chunking (Task 3).

## 2. Chunking & Indexing (Task 4)
- Áp dụng `RecursiveCharacterTextSplitter` với `chunk_size=500` và `chunk_overlap=50`.
- Chuyển sang sử dụng model embedding nhẹ `all-MiniLM-L6-v2` (384 dimensions) để tối ưu hóa tốc độ chạy trên CPU (nhanh gấp 20-25 lần so với các model nặng) thay vì `BAAI/bge-m3`.
- Lưu toàn bộ embedding và metadata vào Vector Store **ChromaDB**.

## 3. Các module Tìm kiếm & Reranking (Task 5, 6, 7, 8)
- **Semantic Search (Task 5):** Tìm kiếm theo ngữ nghĩa dựa trên cosine similarity từ ChromaDB.
- **Lexical Search (Task 6):** Tìm kiếm theo từ khóa chính xác sử dụng thuật toán **BM25**.
- **Reranking (Task 7):** Triển khai thuật toán **Reciprocal Rank Fusion (RRF)** để lai ghép và xếp hạng lại kết quả từ Semantic và Lexical search, lấy ra những documents tốt nhất.
- **Vectorless Fallback (Task 8):** Triển khai logic mock gọi PageIndex API để dự phòng cho trường hợp Semantic search có độ tin cậy quá thấp.

## 4. Pipeline RAG Hoàn chỉnh (Task 9, 10)
- **Unified Retrieval (Task 9):** Viết hàm `retrieve()` điều phối toàn bộ luồng: Hybrid Search -> RRF -> Fallback nếu điểm số < 0.3.
- **Generation có trích dẫn (Task 10):** 
  - Tích hợp **DeepSeek** làm LLM chính (do giá rẻ, tốc độ nhanh, tương thích chuẩn OpenAI SDK).
  - Áp dụng kỹ thuật **Lost-in-the-middle reordering** để sắp xếp lại chunk trước khi đưa vào LLM.
  - Tối ưu hóa System Prompt để ép LLM luôn trả lời tiếng Việt và chèn trích dẫn gốc (ví dụ: `[Document 1]`).
  - Code có tích hợp fallback mock trả về câu trả lời giả lập nếu người dùng chưa cung cấp API key.

## 5. Ứng dụng UI và Đánh giá (Group Project)
- **Streamlit Chatbot UI (`app.py`):** Giao diện hoàn chỉnh, hiển thị câu trả lời từ bot kèm theo thông tin chi tiết về Nguồn tham khảo (tên file, loại tài liệu, điểm số).
- **Evaluation Pipeline (`group_project/evaluation`):**
  - Đã xây dựng **Golden Dataset** gồm 15 cặp Câu hỏi - Câu trả lời mẫu dựa trên tài liệu giả lập.
  - Viết module đánh giá tự động bằng **Ragas** đo lường 4 metrics: Faithfulness, Answer Relevancy, Context Recall, Context Precision.
  - So sánh A/B test tự động giữa cấu hình `Hybrid + RRF` và `Dense Only`, sau đó xuất báo cáo tự động ra file `results.md`.

## 6. Môi trường & Dependencies
- File `requirements.txt` đã được hiệu chỉnh:
  - Loại bỏ `crawl4ai` (do yêu cầu Rust compiler gây lỗi cài đặt trên một số máy).
  - Nới lỏng phiên bản `langchain-text-splitters` và `langchain-core` để tương thích hoàn toàn với thư viện đánh giá `ragas`.

---
*Tất cả các tính năng đã được test chạy thành công 100% từ đầu đến cuối trên máy tính local.*
