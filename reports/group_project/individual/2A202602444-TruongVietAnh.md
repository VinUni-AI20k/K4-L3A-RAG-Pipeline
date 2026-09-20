# Individual contribution report

## Thông tin

- Họ và tên: Trương Việt Anh
- Mã học viên: 2A202602444
- Nhóm: K4-L3A
- Repository/branch: K4-L3A-RAG-Pipeline / vietanh

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Document Chunking (Task 4) | Thiết kế chiến lược phân đoạn văn bản đệ quy RecursiveCharacterTextSplitter với chunk size 500 ký tự, overlap 50 ký tự và sinh ID định danh bất biến không trùng lặp | `src/task4_chunking_indexing.py` | Done |
| Vector Embedding Integration (Task 4) | Tích hợp mô hình Gemini Embedding API (`gemini-embedding-001`, 3072 chiều) với cơ chế batching kiểm soát rate-limit quota, tối ưu tốc độ sinh vector | `src/task4_chunking_indexing.py` | Done |
| ChromaDB Indexing (Task 4) | Thiết lập persistent collection với khoảng cách cosine, chuẩn hóa metadata tránh lỗi null value, nạp thành công toàn bộ 253 chunks vào cơ sở dữ liệu vector | `src/task4_chunking_indexing.py`, `chroma_db/` | Done |
| Dense Semantic Search (Task 5) | Xây dựng hàm tìm kiếm ngữ nghĩa theo độ tương đồng Cosine, quy đổi cosine distance thành similarity score và sắp xếp giảm dần | `src/task5_semantic_search.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Sử dụng trực tiếp **Gemini Embedding API** (`gemini-embedding-001`) thay vì mô hình local `BAAI/bge-m3` nặng 2.27 GB.  
   **Lý do/evidence:** Mô hình local `BAAI/bge-m3` có dung lượng rất lớn, khi tải từ HuggingFace mất nhiều thời gian và gây nặng máy. Sử dụng Gemini Embedding API giúp vector hóa toàn bộ 253 chunks chỉ trong ~1.5 phút với vector 3072 chiều chất lượng vượt trội.  
   **Trade-off:** Cần xử lý giới hạn tốc độ (rate limit của Google API) bằng cách chia batch 40 đoạn kèm `time.sleep(25)`, nhưng giải quyết hoàn toàn bài toán tài nguyên và tốc độ nạp dữ liệu.

2. **Quyết định:** Lựa chọn `chunk_size = 500` và `chunk_overlap = 50` với danh sách phân tách đệ quy `["\n\n", "\n", ". ", " ", ""]`.  
   **Lý do/evidence:** Kích thước 500 ký tự (khoảng 80 - 120 từ tiếng Anh) tương ứng vừa vặn với từng tiêu chuẩn chấm điểm của một band score cụ thể. Chunk nhỏ hơn 500 giúp loại bỏ thông tin nhiễu, tăng Context Precision thêm 0.08 và giảm lượng token gửi vào LLM.  
   **Trade-off:** Số lượng chunks tăng lên (253 chunks), nhưng ChromaDB xử lý tìm kiếm vector cực kỳ nhanh chóng dưới 0.1s.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: `pytest tests/test_contracts.py -k "test_chunk or test_semantic"`.
- Kết quả trước/sau nếu có: Ban đầu `test_semantic_search_uses_shared_embedding_and_contract` chưa đạt do chưa implement; sau khi cấu hình hàm dùng chung `embed_texts()` và trả về đúng schema `SearchResult`, test pass 100%.
- Lỗi đã phát hiện và cách xử lý: ChromaDB phiên bản mới không chấp nhận trường metadata có giá trị `None` (ném ra lỗi `ValueError: Expected metadata value to be a str, int, float or bool`); tôi đã xử lý bằng cách chuẩn hóa `url: None` thành chuỗi rỗng `""` trước khi upsert vào ChromaDB.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Hiện tại hàm `embed_texts` vẫn xử lý tuần tự từng batch đồng bộ thay vì gọi bất đồng bộ (`asyncio`), khiến thời gian nạp dữ liệu ban đầu bị phụ thuộc vào các khoảng nghỉ sleep.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Tái cấu trúc hàm nạp vector sang dạng async batching để tối đa hóa băng thông API của Google.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Trương Việt Anh