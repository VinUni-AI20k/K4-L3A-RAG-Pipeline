# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Hải Long
- Mã học viên: 2A202602471
- Nhóm: GICUNGDC
- Repository/branch: https://github.com/thangws4/K4-Day08-GICUNGDC / nhánh `long2711`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Data Crawling & Clean (Tasks 1-4) | Thu thập văn bản pháp quy, bài báo chuẩn hóa định dạng, giải quyết merge conflict | `data/landing/`, `data/standardized/` | Done |
| Lexical Search & Safe BM25 (Task 6) | Xây dựng BM25Okapi với Lucene IDF chống chia cho 0 trên tập dữ liệu nhỏ | `src/task6_lexical_search.py` | Done |
| Hybrid RRF Fusion (Task 7) | Hợp nhất xếp hạng Dense và Sparse qua Reciprocal Rank Fusion ($k=60$) | `src/task7_rrf.py` | Done |
| Fallback & Orchestrator (Tasks 8, 9) | Pipeline điều phối Hybrid RAG và PageIndex fallback an toàn khi Dense score thấp | `src/task8_pageindex_vectorless.py`, `src/task9_retrieval_pipeline.py` | Done |
| Generation with Citation (Task 10) | Reorder ngữ cảnh chống lost-in-the-middle, sinh câu trả lời kèm trích dẫn số hiệu từ Gemini | `src/task10_generation.py` | Done |
| User Interface & Fullstack App | Xây dựng giao diện Streamlit `app.py` và Fullstack Vercel AI Chatbot `api_server.py` | `app.py`, `api_server.py`, `frontend/` | Done |

## Quyết định kỹ thuật quan trọng

Mô tả tối đa hai quyết định mà bạn trực tiếp tham gia:

1. **Quyết định:** Chuẩn hóa thuật toán BM25Okapi sang công thức Lucene IDF (`k1=1.5, b=0.75`).  
   **Lý do/evidence:** Trên các bộ dữ liệu nhỏ hoặc test fixture có số lượng văn bản ít ($N=2$), công thức BM25 truyền thống cho ra $IDF=0$ đối với các từ xuất hiện trong mọi tài liệu, làm triệt tiêu điểm BM25 về 0. Lucene IDF đảm bảo điểm số luôn dương và bảo toàn thứ hạng tần suất thuật ngữ.  
   **Trade-off:** Điểm số BM25 có biên độ khác một chút so với BM25 nguyên bản, nhưng tuyệt đối ổn định và vượt qua mọi contract test.

2. **Quyết định:** Thiết kế cơ chế Safe Refusal và Citation Grounding chặt chẽ trong Task 10.  
   **Lý do/evidence:** Đối với lĩnh vực Luật Giao thông, việc bịa thông tin (hallucination) gây hậu quả nghiêm trọng. Khi điểm truy xuất không đủ ngưỡng tin cậy hoặc gặp lỗi kết nối API, hệ thống kiên quyết trả về thông điệp từ chối an toàn thay vì phỏng đoán.  
   **Trade-off:** Một số câu hỏi mở hoặc có biên ngữ nghĩa rộng sẽ bị từ chối trả lời, nhưng bù lại bảo đảm 100% câu trả lời được sinh ra đều có căn cứ pháp lý rõ ràng.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: `pytest tests/test_contracts.py -q`, `pytest tests/test_acceptance.py -q`, `pytest -q`.
- Kết quả trước/sau nếu có: Toàn bộ **20/20 test cases passed (100%)**.
- Lỗi đã phát hiện và cách xử lý: Phát hiện và xử lý lỗi client closed exception khi khởi tạo Gemini Client bằng cách khởi tạo `genai.Client(api_key=api_key)` tường minh, giúp sinh câu trả lời đầy đủ và gắn trích dẫn `[Document X]`.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Các file PDF dạng ảnh scan hiện tại mới chỉ được trích xuất metadata do chưa tích hợp OCR tiếng Việt chuyên sâu.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Tích hợp thư viện OCR (như PaddleOCR hoặc Tesseract) để bóc tách toàn văn các bản scan công báo và bổ sung cơ chế re-ranking bằng cross-encoder.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Hải Long
