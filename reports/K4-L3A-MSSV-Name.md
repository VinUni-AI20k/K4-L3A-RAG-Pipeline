# Báo cáo Cá nhân

**Họ và tên:** Nguyễn Văn A (Nhập tên bạn vào đây)
**MSSV:** 20210000 (Nhập MSSV vào đây)
**Vai trò trong nhóm:** Leader / All-rounder

## Các đóng góp chính
1. **Thu thập dữ liệu:** Code script tự động sinh dữ liệu giả lập (chính sách Shopee) tránh bị chặn bởi WAF/Captcha. Chuyển đổi dữ liệu sang định dạng Markdown để chuẩn bị cho RAG.
2. **Chunking & Indexing:** Chuyển đổi mô hình Embedding từ mô hình nặng sang `all-MiniLM-L6-v2` để tối ưu cho hệ thống CPU, đảm bảo pipeline chạy mượt mà.
3. **Retrieval (Dense & Lexical):** Xây dựng hai đường retrieval (Tìm kiếm semantic bằng ChromaDB cosine similarity, tìm kiếm lexical bằng thuật toán BM25).
4. **Reranking:** Viết thuật toán lai ghép Reciprocal Rank Fusion (RRF) kết hợp kết quả từ Dense và Sparse, đẩy điểm những văn bản xuất hiện ở cả hai nơi lên cao.
5. **Generation & Fallback:** Tích hợp thành công DeepSeek API. Viết code chèn Citation, thiết kế luồng Fallback cho những query ngoài lề (trả về Safe Refusal).
6. **UI & Evaluation:** Kết nối pipeline lên Streamlit. Chạy module Ragas đánh giá tự động và báo cáo A/B Test.
