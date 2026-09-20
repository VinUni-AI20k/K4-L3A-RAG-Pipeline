# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Tiến Đạt
- Mã học viên: 2A202602606
- Nhóm: K4-L3A
- Repository/branch: https\://github.com/hoanganhb680-arch/K4-L3A-RAG-Pipeline/tree/ntiendat01/-
trđã thực hiện

| Module/deliverable                     | Việc tôi trực tiếp làm                                                                                                                                                          | File/commit/PR                                                                                                              | Trạng thái |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ---------- |
| Task 1 - Thu thập tài liệu chính sách  | Chuẩn bị thư mục landing cho tài liệu legal, định nghĩa danh sách nguồn và logic tải/kiểm tra file PDF đầu vào để phục vụ bước convert.                                         | `src/task1_collect_legal_docs.py`, `data/landing/legal/sl1.pdf`, `data/landing/legal/sl2.pdf`, `data/landing/legal/sl3.pdf` | Done       |
| Task 2 - Crawl bài viết tin tức        | Xây dựng crawler lấy 5 bài viết du lịch/Hạ Long, lưu JSON gồm `url`, `title`, `date_crawled`, `content_markdown`; xử lý trang render bằng browser và chuyển HTML sang Markdown. | `src/task2_crawl_news.py`, `data/landing/news/article_01.json` đến `article_05.json`                                        | Done       |
| Task 3 - Chuẩn hoá Markdown            | Chuyển dữ liệu landing sang Markdown chuẩn trong `data/standardized`, giữ tiêu đề, nguồn và nội dung chính để các module retrieval dùng chung.                                  | `src/task3_convert_markdown.py`, `data/standardized/legal/*.md`, `data/standardized/news/*.md`                              | Done       |
| Task 4 - Chunking, embedding, indexing | Implement luồng load document, chunk theo `RecursiveCharacterTextSplitter`, embed bằng API key, và upsert ChromaDB với ID ổn định, cosine distance.                             | `src/task4_chunking_indexing.py`, `chroma_db/`                                                                              | Done       |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Chuẩn hoá tất cả nguồn về Markdown trước khi chunk/index. **Lý do/evidence:** Task 3 tạo 3 file legal và 5 file news trong `data/standardized`, giúp Task 4 chỉ cần đọc một định dạng thống nhất. **Trade-off:** Cần kiểm tra chất lượng text sau convert, đặc biệt với PDF tiếng Việt có thể lỗi mã hoá ở một số tiêu đề.
2. **Quyết định:** Dùng embedding API cho Task 4 thay vì tải model local. **Lý do/evidence:** Local model có file `pytorch_model.bin` nặng và gây thời gian chờ lâu; cấu hình `.env` dùng `EMBEDDING_PROVIDER=gemini`, `EMBEDDING_MODEL=gemini-embedding-001`. **Trade-off:** Phụ thuộc API key, quota/rate limit và kết nối mạng khi index lại.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - `python -m src.task1_collect_legal_docs`
  - `python -m src.task2_crawl_news`
  - `python -m src.task3_convert_markdown`
  - `.venv/bin/python -m src.task4_chunking_indexing`
- Kết quả trước/sau nếu có:
  - Landing data có 3 file legal PDF và 5 file news JSON.
  - Standardized data có 8 file Markdown: 3 legal, 5 news.
  - Task 4 đã index thành công `395 chunks` vào ChromaDB.
- Lỗi đã phát hiện và cách xử lý:
  - Tránh tải embedding model local quá nặng bằng cách chuyển sang embedding qua API key.
  - Xử lý metadata `None` trước khi upsert vào ChromaDB để tránh lỗi schema metadata.
  - Với Gemini API, cần batch embedding và chú ý rate limit khi chạy lại toàn bộ corpus.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Chất lượng Markdown sau khi convert PDF vẫn cần rà soát thủ công thêm, vì một số file PDF tiếng Việt có thể bị lỗi dấu hoặc nhiễu layout.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Thêm cơ chế skip các chunk đã có trong ChromaDB để chạy lại Task 4 nhanh hơn và không tốn quota embedding API.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Tiến Đạt
