# Danh sách thành viên và phân công

| Họ và tên | Mã học viên | Vai trò | Nhánh | Phần việc và file phụ trách |
|---|---|---|---|---|
| Lê Duy Quân | 2A202602731 | Data Engineer | `name/leduyquan_2A202602731` | Thu thập tài liệu pháp lý, crawl bài viết và chuẩn hóa Markdown. Phụ trách `src/task1_collect_legal_docs.py`, `src/task2_crawl_news.py`, `src/task3_convert_markdown.py` và `data/`. |
| Vũ Minh Hoàng | 2A202602371 | Retrieval Engineer | `name/vuminhhoang_2A202602371` | Chunking, embedding, ChromaDB, semantic search, BM25 và RRF. Phụ trách `src/task4_chunking_indexing.py` đến `src/task7_reranking.py`. |
| Nguyễn Lê Phúc Thắng | 2A202602638 | RAG Integration & UI Engineer | `name/nguyenlephucthang_2A202602638` | PageIndex fallback, hợp nhất retrieval pipeline, sinh câu trả lời có citation và giao diện chatbot. Phụ trách `src/task8_pageindex_vectorless.py`, `src/task9_retrieval_pipeline.py`, `src/task10_generation.py` và `app.py`. |
| Bùi Trọng Trịnh | 2A202602861 | QA, Evaluation & Documentation | `name/buitrongtrinh_2A202602861` | Golden dataset, đánh giá 4 metrics, so sánh A/B, kiểm thử và tài liệu bàn giao. Phụ trách `group_project/evaluation/`, `reports/`, `README.md`, `pyproject.toml`, `.env.example` và `TEAMMATES.md`. |

## Quy ước để tránh conflict

- Mỗi thành viên chỉ chỉnh sửa các file và thư mục được giao trên nhánh của mình.
- Không sửa `tests/` hoặc `src/contracts.py`; dùng các file này làm contract chung để kiểm tra phần triển khai.
- Nếu cần thêm dependency hoặc biến môi trường, gửi tên dependency/biến cho Bùi Trọng Trịnh tổng hợp vào `pyproject.toml` hoặc `.env.example`.
- Dữ liệu sinh tự động như vector database, cache, file `.env` và API key không được commit.
- Mỗi pull request cần ghi rõ module đã làm, cách chạy và kết quả test liên quan.

## Thứ tự tích hợp đề xuất

1. `name/leduyquan_2A202602731`
2. `name/vuminhhoang_2A202602371`
3. `name/nguyenlephucthang_2A202602638`
4. `name/buitrongtrinh_2A202602861`

Các nhánh được tách theo file ownership nên có thể phát triển song song. Thứ tự trên chỉ áp dụng khi merge vào `main`, vì các bước sau phụ thuộc đầu ra của các bước trước.
