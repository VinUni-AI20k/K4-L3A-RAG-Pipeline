# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Quang Huy
- Mã học viên: 2A202602421
- Nhóm: K4-L3A
- Repository/branch: `kamitoznguyen-collab/K4-L3A-RAG-Pipeline`, nhánh `Huy`
- Vai trò: **Pipeline Lead** — retrieval, generation và evaluation

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 1–3: thu thập & chuẩn hoá | Sinh corpus synthetic (3 PDF chính sách + 5 bài JSON), convert sang Markdown bằng MarkItDown, chuẩn hoá khoảng trắng do PDF trích ra | `src/task1_collect_legal_docs.py`, `src/task2_crawl_news.py`, `src/task3_convert_markdown.py` | Done |
| Task 4: chunking & indexing | `RecursiveCharacterTextSplitter` (500/50), `embed_texts()` dispatch theo provider, upsert ChromaDB cosine với ID ổn định | `src/task4_chunking_indexing.py` | Done |
| Task 5–6: dense & lexical | Semantic search qua ChromaDB, BM25Okapi trên cùng bộ chunks để ID khớp nhau | `src/task5_semantic_search.py`, `src/task6_lexical_search.py` | Done |
| Task 7: RRF | Fuse nhiều ranked list theo `sum(1/(k+rank))`, dedupe theo `id` | `src/task7_reranking.py` | Done |
| Task 8: vectorless fallback | Gọi PageIndex API thật, timeout + cache doc ID, thiếu key thì trả rỗng | `src/task8_pageindex_vectorless.py` | Partial — chưa có API key để chạy end-to-end |
| Task 9: retrieval pipeline | Điều phối dense + BM25 → RRF một lần → fallback theo cosine score gốc; hiệu chỉnh `SCORE_THRESHOLD` | `src/task9_retrieval_pipeline.py` | Done |
| Task 10: generation | Lost-in-the-middle reordering, context kèm title/source, citation `[Document N]`, safe refusal | `src/task10_generation.py` | Done |
| Chatbot UI | Streamlit hiển thị câu trả lời + panel nguồn (title, file, doc_type, chunk index, score, retrieval method) | `app.py` | Done |
| Evaluation | Golden dataset 15 câu kèm đoạn văn gốc; pipeline Ragas 4 metric, A/B dense-only vs hybrid+RRF, xuất báo cáo | `group_project/evaluation/` | Done |

Kiểm chứng: `pytest -q` → 20/20 pass (15 contract + 5 acceptance).

Thành viên khác (khvavuong) dựng khung repo, `pyproject.toml` và template báo cáo
(commit `7a43099`–`6a2a2d4`).

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Bỏ `all-MiniLM-L6-v2`, chuyển sang `paraphrase-multilingual-MiniLM-L12-v2`.
   **Lý do/evidence:** Đo trên corpus thật, model tiếng Anh chấm query **ngoài miền bằng tiếng Việt** ở 0.58–0.69, chồng lấn hoàn toàn với query trong miền (0.63–0.84) — tức là nó chỉ nhận ra "đây là tiếng Việt" chứ không hiểu nội dung, và không thể đặt ngưỡng fallback ở đâu cả. Bản multilingual tách được hai vùng: in-domain 0.360–0.791, out-of-domain 0.135–0.336, nên chọn `SCORE_THRESHOLD = 0.35`.
   **Trade-off:** Model multilingual nặng hơn bản tiếng Anh (118M so với 22M params) nên index chậm hơn; đổi lại fallback mới có cơ sở hoạt động. Biên giữa hai vùng chỉ rộng 0.024 nên vẫn phải đo lại khi corpus lớn lên.

2. **Quyết định:** RRF fuse theo `id`, không theo `content`.
   **Lý do/evidence:** `chunk_overlap = 50` làm nhiều chunk khác nhau có đoạn text trùng nhau. Fuse theo `content` sẽ gộp chúng làm một và nuốt mất kết quả hợp lệ. Contract test `test_rrf_uses_rank_deduplicates_and_marks_hybrid` bắt đúng trường hợp này.
   **Trade-off:** Phải đảm bảo dense và BM25 dùng chung bộ chunks để ID khớp nhau — BM25 vì thế chạy trên output của `chunk_documents()` chứ không tự tokenize lại tài liệu gốc.

## Kiểm thử và kết quả

- **Test đã dùng:** `pytest tests/test_contracts.py` (15 test, không gọi network) và `pytest tests/test_acceptance.py` (5 test kiểm tra corpus, golden dataset và báo cáo). Kết quả: 20/20 pass.
- **Kết quả A/B (Ragas, 15 câu, DeepSeek làm generator và evaluator):**

  | Metric | A (dense-only) | B (hybrid + RRF) | Δ |
  |---|---:|---:|---:|
  | Faithfulness | 0.939 | 0.961 | +0.022 |
  | Answer relevance | 0.858 | 0.864 | +0.006 |
  | Context recall | 1.000 | 1.000 | +0.000 |
  | Context precision | 0.967 | 0.963 | −0.003 |
  | **Average** | 0.941 | 0.947 | **+0.006** |

- **Lỗi đã phát hiện và cách xử lý:**
  - Ragas gọi `answer_relevancy` với `n=3` nhưng DeepSeek chỉ nhận `n=1` → trả `400 Invalid n value`. Xử lý: đặt `strictness=1`.
  - `BM25Okapi` cho IDF = 0 với mọi từ khi corpus chỉ có 2 tài liệu, khiến filter `score > 0` xoá sạch kết quả. Xử lý: chỉ lọc khi thực sự có chunk ghi điểm dương, và dùng stable sort để thứ tự không đảo khi score bằng nhau.
  - Console Windows (cp1252) không encode được tiếng Việt, mọi script `python -m src.taskN` đều chết với `UnicodeEncodeError`. Xử lý: ép `sys.stdout` sang UTF-8 trong `src/__init__.py`.
  - Hai câu có faithfulness 0.667 nhưng đọc kỹ thì **câu trả lời đúng và có citation đầy đủ**. Nguyên nhân là Ragas tách answer thành từng statement, nên "Có." đứng riêng thành một statement không kiểm chứng được. Đây là lỗi đo chứ không phải lỗi hệ thống — đã ghi vào `group_project/evaluation/analysis.md`.

## Điều còn hạn chế

- Corpus là synthetic, chỉ 8 tài liệu / 16 chunk, và golden dataset được soạn từ chính corpus đó. Điểm Ragas cao chỉ chứng minh pipeline nối đúng từ đầu tới cuối, không chứng minh hệ thống chạy tốt trên tài liệu thật. Chênh lệch A/B chỉ +0.006 — nằm trong vùng nhiễu, chưa đủ để kết luận hybrid thắng dense.
- PageIndex fallback viết xong nhưng chưa kiểm chứng end-to-end vì chưa có `PAGEINDEX_API_KEY`.
- **Nếu có thêm thời gian:** việc đầu tiên tôi làm là thay corpus synthetic bằng tài liệu thật từ nguồn công khai cho phép crawl, rồi chạy lại toàn bộ A/B — vì mọi kết luận hiện tại đều bị giới hạn bởi corpus quá nhỏ.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Quang Huy
