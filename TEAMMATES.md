# Thành viên nhóm K4-L3A

Dự án chatbot RAG hỏi đáp về luật giao thông đường bộ Việt Nam.
Repository: https://github.com/thangws4/K4-Day08-GICUNGDC

> **Cần thống nhất:** tên nhóm đang ghi khác nhau giữa các báo cáo cá nhân —
> hai bản ghi `K4-L3A-RAG-Pipeline`, hai bản ghi `GICUNGDC`.

| Họ và tên | Mã học viên | Vai trò | Nhánh làm việc |
| --- | --- | --- | --- |
| Nguyễn Đức Thắng | 2A202602605 | Dữ liệu và indexing, giao diện | `thangnd` |
| Trần Anh Quân | 2A202602598 | Tầng truy xuất | `tran_anh_quan` |
| Nguyễn Hải Long | 2A202602471 | Pipeline và sinh câu trả lời | commit thẳng vào `main` |
| Ngô Tiến Dũng | 2A202602374 | Đánh giá | `tdung` (đã merge, xoá khỏi remote) |

## Phần việc chi tiết

### Nguyễn Đức Thắng — 2A202602605

**Vai trò:** thu thập dữ liệu, chuẩn hóa, chunking và indexing, giao diện chatbot.

- Task 1 — thu thập 6 văn bản pháp luật từ Công báo, kiểm tra text layer và tính đầy đủ các phần: `src/task1_collect_legal_docs.py`
- Task 2 — crawl 5 bài báo từ baochinhphu.vn, giới hạn vào thân bài: `src/task2_crawl_news.py`
- Task 3 — chuẩn hóa sang Markdown, bỏ header Công báo lặp, nối dòng bị PDF ngắt: `src/task3_convert_markdown.py`
- Task 4 — chunk theo ranh giới điều luật, embed bge-m3, index ChromaDB: `src/task4_chunking_indexing.py`
- Giao diện chatbot và design system: `app.py`, `assets/`, `.streamlit/`
- Golden dataset trích nguyên văn từ corpus và script evaluation: `group_project/evaluation/golden_dataset*.json`, `src/run_evaluation.py`

**Commit:** `14319eb`, `6aa4710`, `5b89001`, `1780a28`, `eb4e015`, `7f2164d`

### Trần Anh Quân — 2A202602598

**Vai trò:** tầng truy xuất — dense, lexical và hợp nhất thứ hạng.

- Task 5 — semantic search trên ChromaDB, đổi cosine distance thành similarity: `src/task5_semantic_search.py`
- Task 6 — BM25 với lớp `SafeBM25Okapi` dùng công thức Lucene IDF, cache index: `src/task6_lexical_search.py`
- Task 7 — Reciprocal Rank Fusion gộp dense và BM25: `src/task7_reranking.py`
- Chạy và pass contract test của tầng truy xuất

**Commit:** `36aaa83` (PR #3 — task 5, 6, 7), `8618289`, `cadeb63`, `af52edb`, `adf5278` (PR #6)

### Nguyễn Hải Long — 2A202602471

**Vai trò:** điều phối pipeline truy xuất, fallback và sinh câu trả lời có citation.

- Task 8 — PageIndex vectorless fallback, xử lý lỗi an toàn: `src/task8_pageindex_vectorless.py`
- Task 9 — pipeline điều phối hybrid + điều kiện kích hoạt fallback: `src/task9_retrieval_pipeline.py`
- Task 10 — sinh câu trả lời bằng Gemini, reorder context, citation `[Document X]`, safe refusal: `src/task10_generation.py`

**Commit:** `d379a65` — chạm đúng ba file task 8, 9, 10

### Ngô Tiến Dũng — 2A202602374

**Vai trò:** đánh giá và đối chiếu acceptance test.

- Golden dataset bản đầu và báo cáo đánh giá: `group_project/evaluation/golden_dataset.json`, `group_project/evaluation/RESULT.md`
- Đối chiếu kết quả với `tests/test_acceptance.py`

**Commit:** `605337f`, `983b50a` (PR #4)

## Báo cáo cá nhân

| Thành viên | File |
| --- | --- |
| Ngô Tiến Dũng | `reports/K4-L3A-2A202602374-NgoTienDung.md` |
| Nguyễn Hải Long | `reports/K4-L3A-2A202602471-NguyenHaiLong.md` |
| Trần Anh Quân | `reports/K4-L3A-2A202602598-TranAnhQuan.md` |
| Nguyễn Đức Thắng | `reports/K4-L3A_2A202602605-NguyenDucThang` |
