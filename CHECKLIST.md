# RAG Pipeline — Sprint Checklist

> **Day 8 Lab — Xây dựng Chatbot RAG với Hybrid Retrieval, Citation & Evaluation**
>
> Thời gian tổng: 3 tiếng | 10 mục chính | Cả nhóm cùng thực hiện theo phân công rõ ràng

---

## 📋 Phân Công Chi Tiết

| # | Mục (STEP_BY_STEP) | Người phụ trách | Trạng thái |
|---|---|---|---|
| 1 | Chọn đề tài | Cả nhóm | ✅ ĐÃ XONG |
| 2 | Cài môi trường | Cả nhóm | ✅ ĐÃ XONG |
| 3 | Thu thập dữ liệu | **Khanh** | 🟡 MỘT PHẦN — legal ✅ / news ⏸️ PENDING |
| 4 | Chuẩn hóa Markdown | **Khanh** | ✅ XONG (legal) — news chờ Part B |
| 5 | Chunk, embedding & index | **Khanh** | 🟡 CODE XONG — 🔴 BỊ CHẶN bởi xung đột torch/numpy |
| 6 | Xây dựng hybrid retrieval | **Minh** | ⏳ CHƯA LÀM |
| 7 | Fallback & retrieval pipeline | **Minh** | ⏳ CHƯA LÀM |
| 8 | Generation có citation | **Minh** | ⏳ CHƯA LÀM |
| 9 | Chatbot & evaluation | **Hùng** | ⏳ CHƯA LÀM |
| 10 | Kiểm tra & nộp bài | *Chưa phân công* | ⏳ CHƯA LÀM |

---

## 👉 Bước Tiếp Theo

**Mục 5 — code đã viết xong, nhưng KHÔNG chạy được vì môi trường `.venv` đang hỏng.** Đây là việc chặn đường găng, phải xử lý trước mọi thứ khác.

- **🔴 ƯU TIÊN 1 — Sửa xung đột torch/numpy/transformers** (xem mục `🔴 BLOCKER` bên dưới). Chừng nào chưa sửa, cả mục 5 lẫn mục 6 của Minh đều không chạy được, vì cả hai đều import `sentence_transformers`.

- **Sau khi sửa môi trường — Khanh chạy lại:**
  ```bash
  .venv/bin/python -m pytest tests/test_contracts.py::test_chunk_documents_preserves_identity_and_metadata tests/test_contracts.py::test_public_function_signatures_are_stable -q
  .venv/bin/python -m src.task4_chunking_indexing
  ```
  - ⚠️ Lệnh thứ hai sẽ tải model `BAAI/bge-m3` (~2+ GB) rồi embed **ước tính 1.500+ chunk** trên CPU — mất nhiều phút đến hàng chục phút. Chạy khi có thời gian, đừng chạy ngay trước lúc demo.

- **Kế tiếp — Minh:** Ngay khi mục 5 chạy xong và `embed_texts()` import được, Minh bắt đầu mục 6. Không cần chờ news.

- **Song song — Hùng:** Soạn trước golden dataset dựa trên **nội dung 4 văn bản luật đã có** (Luật Nhà ở, Luật Kinh doanh BĐS, Luật Bảo vệ người tiêu dùng 2023, mẫu số 1A). *Lưu ý: Bộ luật Dân sự đã bị gỡ, không soạn câu hỏi dựa trên nó.* Viết câu hỏi không cần code chạy được.

- **Khi nào quay lại news:** Trước mục 10, vì `pytest -q` phải xanh toàn bộ mới nộp được.

---

## ⚠️ Ghi Chú Quan Trọng

### Mục 10 — Phân Công Chưa Rõ

- **Individual report:** Mỗi thành viên tự viết phần của mình (copy template từ `group_project/ịndividual/INDIVIDUAL_REPORT.md`)
- **Demo & final check:** Cần 1 người chốt để:
  - Chạy full test suite (`pytest -q`)
  - Kiểm tra repo không leak `.env` / API key / cache
  - Demo live chatbot (1 query đúng domain, 1 query ngoài domain, A/B comparison)
- **Đề xuất:** Khanh hoặc Hùng làm người chốt (hoặc chia sẻ công việc)

### ⏸️ Hệ Quả Của Việc Hoãn Crawl News

1. **Acceptance test sẽ đỏ cho tới khi có news.** `tests/test_acceptance.py` yêu cầu ≥5 file JSON trong `data/landing/news/` và ≥5 file Markdown trong `data/standardized/news/`. Chừng nào chưa crawl thì `pytest tests/test_acceptance.py` không thể pass toàn bộ, và `pytest -q` (mục 10) cũng vậy.

2. **Rủi ro mất điểm rubric.** Tiêu chí "Thu thập & chuẩn hoá dữ liệu" (10đ) yêu cầu ≥3 legal **và** ≥5 news. Hiện chỉ có legal → nhiều khả năng mất một phần trong 10đ này nếu tới lúc nộp vẫn chưa có news.

3. **Corpus chỉ có văn bản luật.** Golden dataset ở mục 9 sẽ chỉ hỏi được về nội dung luật; phần A/B test và các câu hỏi dạng tin tức/thời sự sẽ không có dữ liệu để trả lời. Hùng cần biết điều này khi soạn 15 câu hỏi.

### 🔴 BLOCKER: Xung Đột torch / numpy / transformers trong `.venv`

**Triệu chứng:** chạy `pytest tests/test_contracts.py::test_chunk_documents_preserves_identity_and_metadata` báo `NameError: name 'nn' is not defined`, phát sinh trong chuỗi import `langchain_text_splitters → sentence_transformers → transformers → torch.nn.modules.transformer` — **trước khi** code của task4 chạy dòng nào. Kèm cảnh báo của torch: `Failed to initialize NumPy: _ARRAY_API not found`.

**Nguyên nhân — đã xác minh bằng `pip list` và `uname -m`:**

| Package | Đã cài | Ràng buộc |
|---|---|---|
| `torch` | 2.2.2 | build trên numpy 1.x ABI → **không chịu được numpy 2** |
| `numpy` | 2.4.6 | phá ABI của torch 2.2.2 |
| `transformers` | 5.17.0 | đòi **torch ≥ 2.5** |
| `sentence-transformers` | 6.1.0 | kéo theo transformers 5.x |

Máy chạy **macOS x86_64 (Intel)** — PyTorch **ngừng build wheel macOS Intel sau bản 2.2.2**, nên không có đường nâng torch. Bộ version này mâu thuẫn ba chiều: transformers đòi torch ≥2.5, torch 2.2.2 đòi numpy <2.

**Nguyên nhân gốc:** `pyproject.toml` khai báo `sentence-transformers>=2.2.0,<7` quá lỏng → pip kéo về 6.1.0 → kéo theo transformers 5.17 → vỡ.

**Đây KHÔNG phải lỗi logic trong `task4_chunking_indexing.py`** — code chưa kịp chạy dòng nào.

**Ảnh hưởng:** chặn cả **mục 5 (Khanh)** lẫn **mục 6 (Minh)** — cả hai đều import `sentence_transformers`. Nằm trên đường găng.

**✅ Đã ghim version vào `pyproject.toml`:**
- `numpy>=1.26.0,<2` (trước: `<3`)
- `sentence-transformers>=3.0.0,<4` (trước: `>=2.2.0,<7`)
- `transformers>=4.41.0,<5` (mới thêm, trước đây chỉ là dependency gián tiếp)
- `torch` cố ý **không ghim** — trên Intel pip sẽ tự lấy 2.2.2 (bản cao nhất có), trên arm64/Linux lấy bản mới hơn; cả hai đều chạy được với numpy 1.x + transformers 4.x.

**⏳ CHƯA LÀM — cài lại `.venv` cho khớp:**
- [ ] `.venv/bin/python -m pip install -e ".[dev]"` (pip sẽ hạ numpy/transformers/sentence-transformers xuống)
- [ ] Chạy lại 2 test contract của mục 5 để xác nhận
- [ ] **Minh & Hùng cũng phải cài lại** sau khi pull — nếu không sẽ gặp lại đúng lỗi này

**Ghi chú:** `BAAI/bge-m3` chạy bình thường trên `sentence-transformers` 3.x, việc hạ version không ảnh hưởng chất lượng embedding.

### ✅ Đã Xử Lý: Dependency markitdown[docx]

- **Vấn đề:** `pip install -e ".[dev]"` không kéo theo extras `[docx]` → mọi file `.docx` lỗi `MissingDependencyException`.
- **Đã sửa:** `pyproject.toml` gộp thành một dòng `markitdown[pdf,docx]>=0.1.0,<0.2` (trước đó là hai dòng trùng package, dòng `markitdown[docx]` không có ràng buộc version nên resolver có thể kéo về bản ngoài khoảng cho phép).
- Người clone repo về giờ cài một lệnh là đủ, không cần cài tay.

### 📌 Bài Học: PDF Scan Không Có Text Layer

- `bo-luat-dan-su.pdf` (6.7 MB) nhưng convert ra **0 ký tự** — dấu hiệu điển hình của PDF scan ảnh (image-based, không có text layer).
- **Kích thước file lớn KHÔNG đảm bảo** có text trích xuất được.
- **Cách xử lý đã chọn:** Thay bằng nguồn PDF khác có text layer (`luat_bao_ve_nguoi_tieu_dung_2023.pdf`). Nhanh, vài phút. Cách còn lại là OCR (tốn thời gian, cần cài tesseract).
- **Khuyến nghị:** Nếu sau này bổ sung tài liệu legal mới, hãy kiểm tra số ký tự convert được ngay thay vì tin vào kích thước file.

### Khối Lượng Công Việc Lệch Nhau

- **Khanh:** 20 điểm (mục 3→4→5) — tương đối cân bằng
- **Minh:** 45 điểm (mục 6→7→8) — **gánh nặng nhất**, tương đương ~50% rubric
  - Dense, BM25, RRF: 20đ
  - Pipeline & fallback: 10đ
  - Generation & citation: 15đ
- **Hùng:** 20 điểm (mục 9)
- **Chung:** 5 điểm (mục 10)

**Khuyến nghị:** Nếu kịp, hãy san bớt mục 8 (Generation) sang Hùng hoặc Khanh để cân bằng công việc.

### ✅ Đã Xử Lý: mau-so-1a.docx

- **Lo ngại ban đầu:** File biểu mẫu pháp lý (35 KB) có thể không đạt ≥200 ký tự sau khi convert.
- **Kết quả thực tế:** Sau khi cài `markitdown[docx]`, file convert thành công ra **53.394 ký tự** — vượt xa ngưỡng. **Không cần thay file.**

---

## 🎯 Chi Tiết 10 Mục

### **Mục 1 — Chọn Đề Tài** ⏱️ 5'
**Người phụ trách:** Cả nhóm | **Trạng thái:** ✅ **XONG**

- [x] Chọn chủ đề: **Pháp luật cho hộ kinh doanh** (corpus hẹp lại mảng đất đai / nhà ở / bất động sản)
- [x] Phân công role rõ ràng (Khanh, Minh, Hùng)
- [x] Mỗi thành viên ghi lại commit mình phụ trách (để viết individual report sau)

---

### **Mục 2 — Cài Môi Trường** ⏱️ 5'
**Người phụ trách:** Cả nhóm | **Trạng thái:** ✅ **XONG**

- [x] `python -m venv .venv` + activate
- [x] `pip install -e ".[dev]"`
- [x] `python -m playwright install chromium`
- [x] `cp .env.example .env` và điền API key (⚠️ **KHÔNG commit `.env`**)

---

### **Mục 3 — Thu Thập Dữ Liệu** ⏱️ 20'
**Người phụ trách:** **Khanh** | **Trạng thái:** 🟡 **ĐANG LÀM** (legal ✅ xong, news ⏳ chưa)

#### Part A: Tài Liệu Pháp Lý — **✅ ĐÃ XONG**
- [x] ≥3 PDF/DOCX vào `data/landing/legal/`, mỗi file >1KB
- [x] **Hiện tại:**
  - `luat-nha-o.pdf` (1.4 MB) ✅
  - `luat-kinh-doanh-bds.pdf` (726 KB) ✅
  - `luat_bao_ve_nguoi_tieu_dung_2023.pdf` (623 KB) ✅
  - `mau-so-1a.docx` (35 KB) ✅
  - *Ghi chú:* `bo-luat-dan-su.pdf` (6.7 MB) đã bị gỡ — convert ra 0 ký tự, dấu hiệu PDF scan ảnh không có text layer (markitdown không trích được; muốn dùng phải OCR).

#### Part B: Bài Báo Tin Tức — **⏸️ TẠM HOÃN (PENDING)**

> ⏸️ **Ghi chú:** Nhóm quyết định tạm hoãn phần crawl tin tức ở thời điểm này. Sẽ quay lại sau khi hoàn thành phần legal.

- [ ] Implement `src/task2_crawl_news.py` — `crawl_article()`, `crawl_all()`
- [ ] Crawl ≥5 bài vào `data/landing/news/` dạng JSON
- [ ] Format mỗi file: `{url, title, date_crawled, content_markdown}`
- [ ] Mỗi file >1KB
- [ ] **Lệnh:** `python -m src.task2_crawl_news`

---

### **Mục 4 — Chuẩn Hóa Markdown** ⏱️ 15'
**Người phụ trách:** **Khanh** | **Trạng thái:** ✅ **XONG (phần legal)**

- [x] `src/task3_convert_markdown.py`:
  - [x] `convert_legal_docs()` — chuyển PDF/DOCX → `data/standardized/legal/` (dùng `markitdown`); bỏ qua thư mục rỗng/không tồn tại thay vì raise, mỗi file lỗi convert được bắt riêng và không làm hỏng batch
  - [x] `convert_news_articles()` — chuyển JSON → `data/standardized/news/` (dùng `markitdown` header thủ công); **không raise** khi `data/landing/news/` rỗng/chưa có (in cảnh báo rồi return) để không chặn mục 5
  - [x] Guard ngưỡng ≥200 ký tự trong code: nội dung convert được <200 ký tự (đếm trên phần content, không tính header) thì **không ghi file**, chỉ in cảnh báo — đảm bảo không có file output nào vi phạm ngưỡng test
  - [x] Idempotent: tên file output cố định `{stem}.md`, chạy lại ghi đè, không nhân bản, không để lại file rỗng
- [x] ✅ **Kiểm tra** `mau-so-1a.docx` khi convert — **đạt 53.394 ký tự**, vượt ngưỡng 200 ký tự
- [x] **Lệnh:** `python -m src.task3_convert_markdown` ✅ **Chạy thành công**
- [ ] ✅ **Chốt:** `pytest tests/test_acceptance.py` phần data — legal ✅ PASS, nhưng news PENDING (chưa chạy full test do news rỗng)*

**Kết quả chạy thực tế:**

| File nguồn | File Markdown | Số ký tự | Kết quả |
|---|---|---|---|
| `luat-nha-o.pdf` | `luat-nha-o.md` | 209.458 | ✅ |
| `luat-kinh-doanh-bds.pdf` | `luat-kinh-doanh-bds.md` | 145.203 | ✅ |
| `luat_bao_ve_nguoi_tieu_dung_2023.pdf` | `luat_bao_ve_nguoi_tieu_dung_2023.md` | 111.198 | ✅ |
| `mau-so-1a.docx` | `mau-so-1a.md` | 53.394 | ✅ |

**4/4 file convert thành công, 0 file bị bỏ qua. Tất cả vượt xa ngưỡng 200 ký tự.**

**Ghi chú:** Dependency `markitdown[docx]` đã được cài để hỗ trợ convert `.docx`. Vấn đề ban đầu là phần code cần handle trường hợp `data/landing/news/` rỗng để không crash mục 5 — đã implement xong và chạy thành công.

---

### **Mục 5 — Chunk, Embedding & Index** ⏱️ 15'
**Người phụ trách:** **Khanh** | **Trạng thái:** 🟡 **CODE XONG — 🔴 BỊ CHẶN bởi môi trường**

- [x] `src/task4_chunking_indexing.py` — đã implement đầy đủ:
  - [x] Giữ nguyên hằng số: `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`, `CHUNKING_METHOD="recursive"`, `EMBEDDING_MODEL="BAAI/bge-m3"`, `EMBEDDING_DIM=1024`, `COLLECTION_NAME="rag_documents"`
  - [x] `load_documents()` — rglob `.md`, bỏ file ẩn/rỗng, `doc_type` suy từ thư mục cha, `id` = đường dẫn tương đối posix. **Không crash khi `news/` rỗng** (in cảnh báo, trả list).
  - [x] `chunk_documents(documents)` — `RecursiveCharacterTextSplitter`, `chunk_index` 0-based theo từng document, metadata copy riêng cho mỗi chunk (không share reference)
  - [x] `embed_texts(texts)` — dispatch theo `EMBEDDING_PROVIDER` trong `.env` (mặc định `sentence_transformers`, có nhánh openai/gemini), model cache lazy ở cấp module, trả `[]` khi input rỗng mà không load model
  - [x] `embed_chunks(chunks)` — embed batch 32, in tiến độ, `raise ValueError` nếu dimension thực tế ≠ 1024
  - [x] `get_collection()` — `PersistentClient` + `hnsw:space=cosine`
  - [x] `index_to_vectorstore(chunks)` — dùng **`upsert`** (không phải `add`) để re-index không nhân bản, batch 100
  - [x] **ID chunk:** `{doc_id}::chunk-{index}` (0-based)

- [x] **Ràng buộc ≤550 ký tự** (`tests/test_contracts.py:113`) — có lưới an toàn `_split_oversized()`: đoạn nào splitter trả về vượt `_HARD_MAX_CHUNK_CHARS = 550` bị cắt cứng. Không tin vào việc splitter luôn tôn trọng `chunk_size`.

- [x] **`metadata.title` dùng tên văn bản thật**, trích từ chính nội dung file (`DOCUMENT_TITLES`):

| File | Title |
|---|---|
| `luat-nha-o.md` | Luật Nhà ở (Luật số 27/2023/QH15) |
| `luat-kinh-doanh-bds.md` | Luật Kinh doanh bất động sản (Luật số 29/2023/QH15) |
| `luat_bao_ve_nguoi_tieu_dung_2023.md` | Luật Bảo vệ quyền lợi người tiêu dùng (Luật số 19/2023/QH15) |
| `mau-so-1a.md` | Mẫu số Ia: Nội dung hợp đồng mẫu áp dụng trong mua bán căn hộ chung cư |

  Fallback nếu file mới không có trong dict: heading `#` đầu tiên → `path.stem`.

- [ ] **`metadata.url` hiện đều là `None`** (`DOCUMENT_URLS` để trống sẵn). Contract ghi `url: str | None` nên **hợp lệ, không vi phạm** — nhưng citation ở Mục 8 sẽ không dẫn ngược về văn bản gốc được. Nhóm điền URL đã xác minh vào dict này nếu muốn citation đầy đủ.

- [x] ✅ **Chốt 1:** `test_public_function_signatures_are_stable` — **PASS**
- [ ] 🔴 **Chốt 2:** `test_chunk_documents_preserves_identity_and_metadata` — **FAIL**, nhưng **không phải lỗi logic**: import `sentence_transformers` vỡ vì xung đột torch/numpy (xem mục 🔴 BLOCKER ở trên). Chưa xác minh được logic bằng thực thi.
- [ ] **Lệnh (chạy sau khi sửa môi trường):** `.venv/bin/python -m src.task4_chunking_indexing`
  - ⚠️ Tải model ~2+ GB, embed ước tính **1.500+ chunk** trên CPU → mất nhiều phút đến hàng chục phút
- [x] **🔗 Bàn giao cho Minh:** `embed_texts()` là hàm cấp module, import được từ `src.task4_chunking_indexing`

---

### **Mục 6 — Xây Dựng Hybrid Retrieval** ⏱️ 20'
**Người phụ trách:** **Minh** | **Trạng thái:** ⏳ **CHƯA LÀM**

#### Part A: Dense Search
- [ ] `src/task5_semantic_search.py`:
  - [ ] **⚠️ QUAN TRỌNG:** `from src.task4_chunking_indexing import embed_texts` — **KHÔNG** tự load model mới
  - [ ] Implement: `semantic_search(query, top_k=10)` trả `SearchResult`
  - [ ] `retrieval_method="dense"`, sort score giảm dần
  - [ ] **Lệnh:** `python -m src.task5_semantic_search`
  - [ ] ✅ **Chốt:** `pytest tests/test_contracts.py::test_semantic_search_uses_shared_embedding_and_contract` **PASS**

#### Part B: Lexical Search (BM25)
- [ ] `src/task6_lexical_search.py`:
  - [ ] Implement: `build_bm25_index(corpus)`, `lexical_search(query, top_k=10)`
  - [ ] Maintain global `CORPUS` — chạy trên **cùng chunks** với Dense
  - [ ] `retrieval_method="bm25"`, cùng schema `SearchResult`
  - [ ] **Lệnh:** `python -m src.task6_lexical_search`
  - [ ] ✅ **Chốt:** `pytest tests/test_contracts.py::test_lexical_search_returns_bm25_contract` **PASS**

#### Part C: RRF Fusion
- [ ] `src/task7_reranking.py`:
  - [ ] Implement: `rerank_rrf(ranked_lists, top_k=5, k=60)`
  - [ ] Công thức: `score = Σ 1/(k + rank)`, rank từ 1
  - [ ] Deduplicate theo `id`, sort giảm dần, gắn `retrieval_method="hybrid"`
  - [ ] **Lệnh:** `python -m src.task7_reranking`
  - [ ] ✅ **Chốt:** `pytest tests/test_contracts.py::test_rrf_uses_rank_deduplicates_and_marks_hybrid` **PASS**
- [ ] **Lưu ý:** Reranker nâng cao (Jina, self-host BGE) **không bắt buộc** — có thể để bonus

---

### **Mục 7 — Fallback & Retrieval Pipeline** ⏱️ 20'
**Người phụ trách:** **Minh** | **Trạng thái:** ⏳ **CHƯA LÀM**

#### Part A: Fallback Retrieval (PageIndex)
- [ ] `src/task8_pageindex_vectorless.py`:
  - [ ] Implement: `upload_documents()`, `pageindex_search(query, top_k=5)`
  - [ ] `retrieval_method="pageindex"`, bọc try/except
  - [ ] ⚠️ Lỗi API **KHÔNG** được crash pipeline (trả list rỗng)

#### Part B: Orchestration
- [ ] `src/task9_retrieval_pipeline.py`:
  - [ ] Implement: `retrieve(query, top_k=5, score_threshold=0.3, use_reranking=True)`
  - [ ] **Luồng logic chặt chẽ:**
    - [ ] Chạy Dense + BM25 với `top_k*2` kết quả (mỗi cái độc lập)
    - [ ] RRF gộp hai bảng xếp hạng **đúng MỘT lần**
    - [ ] So ngưỡng dùng **cosine score gốc của Dense** trước fusion (KHÔNG dùng RRF score)
    - [ ] Nếu max score Dense < threshold: fallback sang PageIndex
    - [ ] Lỗi PageIndex: trả kết quả Hybrid (không crash)
  - [ ] **Lệnh:** `python -m src.task9_retrieval_pipeline`
  - [ ] ✅ **Chốt:** Test fallback behavior, test RRF called once, test dense score used for threshold

- [ ] **Calibrate threshold:** Chạy query vừa trong domain vừa ngoài domain → đo dense score thực tế
  - Không có con số đúng cho mọi corpus — **phải tự đo**

---

### **Mục 8 — Generation Có Citation** ⏱️ 20'
**Người phụ trách:** **Minh** | **Trạng thái:** ⏳ **CHƯA LÀM**

- [ ] `src/task10_generation.py`:
  - [ ] Hằng số: `TEMPERATURE=0.3`, `TOP_P=0.9`
  - [ ] Implement: `reorder_for_llm(chunks)` — reorder chống lost-in-the-middle
    - [ ] **KHÔNG mutate input**, **KHÔNG làm mất ID**
  - [ ] Implement: `format_context(chunks)` — context phải có Title + Source
  - [ ] Implement: `call_llm(system_prompt, user_message)` — dispatch theo `LLM_PROVIDER` (openai / gemini / anthropic)
  - [ ] Implement: `generate_with_citation(query, top_k=5)` trả `GenerationResult`
    - [ ] Safe refusal: Sources rỗng ⇒ trả `{answer: "Không có dữ liệu...", sources: [], retrieval_source="none"}`
  - [ ] **Lệnh:** `python -m src.task10_generation`
  - [ ] ✅ **Chốt:** `pytest tests/test_contracts.py::test_reorder_is_non_mutating_and_context_contains_source` **PASS**

---

### **Mục 9 — Chatbot & Evaluation** ⏱️ 30'
**Người phụ trách:** **Hùng** | **Trạng thái:** ⏳ **CHƯA LÀM**

> **Phụ thuộc:** Mục này chỉ run được khi Minh xong mục 8. Trong khi chờ, Hùng nên chuẩn bị golden dataset & khung `app.py`.

#### Part A: Streamlit App
- [ ] `app.py` — `streamlit run app.py`:
  - [ ] Hiển thị: **answer** + **sources** (list) + **retrieval_method** + **score**
  - [ ] Không crash khi retrieval error hoặc LLM error

#### Part B: Golden Dataset
- [ ] `group_project/evaluation/golden_dataset.json` — **≥15 golden Q&A:**
  - [ ] Mỗi item: `{question, expected_answer, expected_context}`
  - [ ] Câu hỏi phải vừa chủ đề, vừa có dữ liệu để trả lời

#### Part C: RAGAS Evaluation
- [ ] Chạy 4 metric RAGAS: `faithfulness`, `answer_relevance`, `context_recall`, `context_precision`
- [ ] A/B test: **Dense-only vs Hybrid + RRF** (chỉ đổi retrieval method, cấu hình khác giữ nguyên)

#### Part D: Result Report
- [ ] `group_project/evaluation/RESULT.md`:
  - [ ] Bảng A/B kết quả 4 metric
  - [ ] Phân tích worst cases (câu kém nhất, kết quả kém nhất)
  - [ ] Khuyến nghị cải thiện
  - [ ] ⚠️ **KHÔNG được còn chữ "TODO"** (acceptance test check literal)

---

### **Mục 10 — Kiểm Tra & Nộp Bài** ⏱️ 15'
**Người phụ trách:** *Chưa phân công — đề xuất cả nhóm* | **Trạng thái:** ⏳ **CHƯA LÀM**

- [ ] **Mỗi thành viên:** Copy template `group_project/ịndividual/INDIVIDUAL_REPORT.md` → `reports/{mssv}-{ten}.md`
  - [ ] Khanh: phần mục 3→5 của bạn
  - [ ] Minh: phần mục 6→8 của bạn
  - [ ] Hùng: phần mục 9 của bạn
  - [ ] Chung: commit, thứ tự phụ thuộc, khó khăn gặp phải
- [ ] **Người chốt** (TBD): Chạy kiểm tra cuối cùng
  - [ ] `pytest tests/test_contracts.py -q` — **PASS**
  - [ ] `pytest tests/test_acceptance.py -q` — **PASS**
  - [ ] `pytest -q` — **PASS**
  - [ ] `grep -r "\.env" .` — KHÔNG leak `.env`
  - [ ] `grep -rE "(OPENAI_API_KEY|GEMINI_API_KEY|ANTHROPIC_API_KEY)" src/ --include="*.py"` — KHÔNG hard-code API key
  - [ ] Kiểm tra cache (`.pkl`, `.index`, `chroma_data`) có được `.gitignore` không
- [ ] **Demo live:**
  - [ ] Query 1: **Trong domain** (e.g., "Hộ kinh doanh cần những giấy tờ gì để mua nhà?") → kỳ vọng dense + BM25 chạy tốt
  - [ ] Query 2: **Ngoài domain** (e.g., "Công thức nấu ăn gì?") → kỳ vọng fallback PageIndex hoặc safe refusal
  - [ ] A/B: So sánh dense-only vs hybrid (nếu có thời gian)
- [ ] Push repo

---

## 📊 Bảng Schema Tham Chiếu

| Kiểu | Cấu trúc |
|------|----------|
| **Document** | `{id, content, metadata:{source, title, doc_type:"legal"\|"news", url}}` |
| **Chunk** | `{id:"{doc_id}::chunk-{i}", content, metadata:{source, title, doc_type, url, chunk_index}}` |
| **SearchResult** | `{id, content, score:float, metadata, retrieval_method:"dense"\|"bm25"\|"hybrid"\|"pageindex"}` |
| **GenerationResult** | `{answer, sources:list[SearchResult], retrieval_source:"hybrid"\|"pageindex"\|"none"}` |

---

## ✅ 8 Bất Biến Bắt Buộc

| # | Bất Biến | Người chịu trách nhiệm |
|---|---|---|
| 1 | ID chunk format `{doc_id}::chunk-{i}`, re-index không nhân bản | **Khanh** |
| 2 | Task 4 & Task 5 dùng **chung** `embed_texts()`, dim=1024 | **Khanh↔Minh** |
| 3 | SearchResult sort **giảm dần**, no dup, ≤`top_k` | **Minh** |
| 4 | RRF chạy **đúng 1 lần** trong pipeline (task9) | **Minh** |
| 5 | Threshold fallback dùng **cosine Dense** (không phải RRF score) | **Minh** |
| 6 | Không hard-code API key, chỉ từ `.env` | **Cả nhóm** |
| 7 | Lỗi provider (PageIndex, LLM) KHÔNG crash pipeline | **Minh** |
| 8 | Citation map được về list `sources` (SearchResult) | **Minh** |

---

## 🚨 3 Bẫy Mất Điểm Nhiều Nhất

### **Trap 1: Embedding Không Dùng Chung** ❌ Task 5
- **Vấn đề:** Task 5 tự load model riêng → fail `test_semantic_search_uses_shared_embedding_and_contract`
- **Mất:** 10-20 điểm (contract test + consistency)
- **Fix:** `from src.task4_chunking_indexing import embed_texts`

### **Trap 2: Threshold Dùng RRF Score** ❌ Task 9
- **Vấn đề:** RRF score (~0.016) luôn nhỏ hơn mọi ngưỡng cosine hợp lý (0.3+) → fallback kích hoạt 100%
- **Mất:** 10 điểm (pipeline logic)
- **Fix:** So sánh dùng **cosine score gốc của Dense** trước RRF fusion

### **Trap 3: RRF Chạy Hai Lần** ❌ Task 7 & Task 9
- **Vấn đề:** Fuse ở task7, rồi fuse lại ở task9 → test đếm lần gọi fail
- **Mất:** 5-10 điểm (contract test)
- **Fix:** Task 7 chỉ export hàm, task 9 gọi **đúng 1 lần duy nhất**

---

## 📋 Rubric 90 + 10 Bonus

| Tiêu chí | Điểm | Người phụ trách |
|----------|------|---|
| Thu thập & chuẩn hoá dữ liệu (≥3 docs + ≥5 news + markdown ≥200 ký tự) | 10 | **Khanh** |
| Chunking, embedding, vector DB (ID ổn định, dim=1024) | 10 | **Khanh** |
| Dense, BM25, RRF (score sort, no dup, hybrid mark) | 20 | **Minh** |
| Retrieval pipeline & fallback (threshold logic, 1x RRF) | 10 | **Minh** |
| Generation có citation & safe refusal (non-mutating, sources map) | 15 | **Minh** |
| Chatbot UI end-to-end, hiển thị nguồn (streamlit) | 10 | **Hùng** |
| Golden dataset ≥15 câu, 4 metric, A/B, error analysis | 10 | **Hùng** |
| README, reproducibility, báo cáo cá nhân, no `.env` leak | 5 | **Cả nhóm** |
| **TỔNG 90** | **90** | |

**Bonus (tối đa 10, phải chạy được + có bằng chứng):**
- [ ] HyDE / query expansion có A/B so sánh (+3)
- [ ] Reranker nâng cao vs RRF (+3)
- [ ] Conversation memory cho follow-up (+2)
- [ ] Deploy online hoặc highlight citation trên UI (+2)

---

## 🔍 Lệnh Kiểm Tra Nhanh

```bash
# Contract test (cốt lõi logic)
pytest tests/test_contracts.py -q

# Acceptance test (end-to-end, data)
pytest tests/test_acceptance.py -q

# Tất cả test
pytest -q

# Streamlit app
streamlit run app.py

# Kiểm tra `.env` leak
grep -r "\.env" . --include="*.py"

# Kiểm tra hard-code API key
grep -rE "(OPENAI_API_KEY|GEMINI_API_KEY|ANTHROPIC_API_KEY)" src/ --include="*.py"
```

---

## 📅 Thứ Tự Phụ Thuộc & Timeline

```
Khanh (Mục 3→4→5, ~60') ─→ Minh (Mục 6→7→8, ~60') ─→ Hùng (Mục 9, ~30')
                            ↑ Khanh nộp embed_texts              ↑ Minh nộp mục 8
                            
Trong khi chờ Minh xong, Hùng chuẩn bị golden dataset & khung app.py

Cuối cùng: Cả nhóm (Mục 10, ~15') — chuẩn bị report cá nhân & demo
```

**Ghi chú về News (Mục 3 Part B):** Hiện nằm ngoài đường găng (critical path), có thể chen vào bất cứ lúc nào trước mục 10; nhưng nếu bỏ hẳn thì acceptance test và 10đ rubric dữ liệu sẽ bị ảnh hưởng.

---

## 📝 Ghi Chú Chung

- **Mỗi ✅ chốt** là điểm kiểm tra bắt buộc — nếu test fail, dừng debug trước khi tiến
- **Khanh bàn giao:** `embed_texts()` phải import được ở task5
- **Minh bàn giao:** mục 8 xong mới Hùng chạy được end-to-end
- **Hùng:** chuẩn bị golden dataset & `app.py` skeleton lúc chờ
- **Tất cả:** commit msg phải ghi mục nào, ai làm (để viết report sau)

---

**✏️ Cập nhật lần cuối:** 2026-09-20
