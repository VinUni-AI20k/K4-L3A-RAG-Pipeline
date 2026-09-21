# RAG Pipeline — Sprint Checklist

> **Day 8 Lab — Xây dựng Chatbot RAG với Hybrid Retrieval, Citation & Evaluation**
>
> Thời gian tổng: 3 tiếng | 10 mục chính | Cả nhóm cùng thực hiện theo phân công rõ ràng

---

## 📋 Phân Công Chi Tiết

| # | Mục (STEP_BY_STEP) | Người phụ trách | Trạng thái |
|---|---|---|---|
| 1 | Chọn đề tài | Cả nhóm | ✅ XONG |
| 2 | Cài môi trường | Cả nhóm | ✅ XONG |
| 3 | Thu thập dữ liệu | **Khanh** | 🟡 MỘT PHẦN — legal ✅ 4/4 / news ❌ 0/5 |
| 4 | Chuẩn hóa Markdown | **Khanh** | 🟡 MỘT PHẦN — legal ✅ 4/4 / news ❌ 0/5 |
| 5 | Chunk, embedding & index | **Khanh** | ✅ XONG — 1392 chunk, dim 1024 |
| 6 | Hybrid retrieval (task5/6/7) | **Minh** | ✅ XONG — 15/15 contract tests PASS |
| 7 | Fallback & retrieval pipeline (task8/9) | **Minh** | ✅ XONG — contract tests PASS |
| 8 | Generation có citation (task10) | **Minh** | ✅ XONG — contract tests PASS |
| 9 | Chatbot & evaluation | **Hùng** | 🟡 MỘT PHẦN — `app.py` stub / eval chưa chạy |
| 10 | Kiểm tra & nộp bài | Cả nhóm | ❌ CHƯA LÀM |

---

## ✅ Trạng Thái Contract Tests

> Chạy: `pytest tests/test_contracts.py -q`

| Test | Trạng thái |
|---|---|
| `test_public_function_signatures_are_stable` | ✅ PASS |
| `test_document_validator_accepts_contract` | ✅ PASS |
| `test_document_validator_rejects_missing_fields` | ✅ PASS |
| `test_search_result_validator_checks_order_method_and_uniqueness` | ✅ PASS |
| `test_chunk_documents_preserves_identity_and_metadata` | ✅ PASS |
| `test_semantic_search_uses_shared_embedding_and_contract` | ✅ PASS |
| `test_lexical_search_returns_bm25_contract` | ✅ PASS |
| `test_rrf_uses_rank_deduplicates_and_marks_hybrid` | ✅ PASS |
| `test_reorder_is_non_mutating_and_context_contains_source` | ✅ PASS |
| `test_retrieve_uses_dense_score_for_fallback` | ✅ PASS |
| `test_retrieve_fuses_once_when_dense_is_confident` | ✅ PASS |
| `test_retrieve_survives_fallback_provider_error` | ✅ PASS |
| `test_generation_result_validator_accepts_safe_refusal` | ✅ PASS |

**Kết quả:** 15/15 PASS ✅

---

## ❌ Trạng Thái Acceptance Tests

> Chạy: `pytest tests/test_acceptance.py -q`

| Test | Trạng thái | Blocker |
|---|---|---|
| `test_corpus_has_required_legal_documents` | ✅ PASS | — |
| `test_corpus_has_required_news_with_metadata` | ❌ FAIL | `data/landing/news/` rỗng |
| `test_standardized_output_covers_both_source_types` | ❌ FAIL | `data/standardized/news/` rỗng |
| `test_golden_dataset_has_15_grounded_cases` | ✅ PASS | 20 câu ✓ |
| `test_evaluation_report_is_completed` | ❌ FAIL | RESULT.md còn TODO |

---

## 👉 Việc Còn Lại (Ưu Tiên Cao)

### 🔴 1. Crawl News — **Blocker chính**
- `data/landing/news/` hoàn toàn rỗng → 2 acceptance test đang đỏ
- `task2_crawl_news.py`: `ARTICLE_URLS = []` và `crawl_article()` còn `NotImplementedError`
- **Ảnh hưởng:** `pytest -q` không thể pass; mất điểm rubric "Thu thập & chuẩn hoá" (10đ)
- **Người làm:** Khanh hoặc Hùng, thực hiện NGAY, ~30 phút

### 🔴 2. `app.py` (Streamlit) — Cần wire vào pipeline
- Hiện là stub hoàn toàn: trả `"TODO: Itegration RAG Pipeline here"`, không gọi pipeline thật
- Cần: `generate_with_citation(query, top_k)` → hiển thị answer + sources + score
- **Người làm:** Hùng, ~30–45 phút

### 🟡 3. `group_project/evaluation/RESULT.md` — Còn toàn bộ TODO
- Acceptance test check literal `"TODO"` → fail nếu còn
- Cần chạy RAGAS trước rồi điền kết quả thật
- **Phụ thuộc:** `app.py` và task10 phải chạy end-to-end trước

### 🟡 4. Individual Reports — Khanh và Minh chưa có
- `reports/2A202602942-HUNGLM.md`: Hùng có file nhưng **nội dung trống** (chưa điền)
- Khanh và Minh chưa tạo file report
- **Mỗi người làm phần của mình**, ~15 phút

### 🟡 5. `PAGEINDEX_API_KEY` — Chưa điền trong `.env`
- Fallback sẽ silently trả `[]`, không crash nhưng không hoạt động
- Điền key vào `.env` nếu có, chạy `python -m src.task8_pageindex_vectorless` để upload PDF

---

## 🔍 Kiểm Tra Code Theo MODULE_CONTRACTS.md

### Interface Bắt Buộc

| Hàm | Signature | Implement | Ghi chú |
|---|---|---|---|
| `load_documents()` | ✅ | ✅ | task4 |
| `chunk_documents(documents)` | ✅ | ✅ | task4 |
| `embed_texts(texts)` | ✅ | ✅ | task4, dispatch openai/gemini/sentence_transformers |
| `embed_chunks(chunks)` | ✅ | ✅ | task4, batch 32, dim check |
| `get_collection()` | ✅ | ✅ | task4, cosine distance |
| `index_to_vectorstore(chunks)` | ✅ | ✅ | task4, upsert |
| `semantic_search(query, top_k)` | ✅ | ✅ | task5, dùng `embed_texts` từ task4 ✅ |
| `lexical_search(query, top_k)` | ✅ | ✅ | task6, BM25Plus |
| `rerank_rrf(ranked_lists, top_k, k)` | ✅ | ✅ | task7 |
| `pageindex_search(query, top_k)` | ✅ | ✅ | task8, REST API, graceful fail |
| `retrieve(query, top_k, score_threshold, use_reranking)` | ✅ | ✅ | task9 |
| `reorder_for_llm(chunks)` | ✅ | ✅ | task10, non-mutating ✅ |
| `format_context(chunks)` | ✅ | ✅ | task10, có title + source ✅ |
| `generate_with_citation(query, top_k)` | ✅ | ✅ | task10 |

### Quy Tắc Bắt Buộc

| Quy tắc | Trạng thái | Ghi chú |
|---|---|---|
| `id` duy nhất và ổn định | ✅ | `{path}::chunk-{i}`, upsert |
| Chunk không rỗng, có `chunk_index` | ✅ | filter + 0-based per-doc |
| Task 4 & 5 dùng chung `embed_texts()` | ✅ | task5 import từ task4 |
| SearchResult sort giảm dần, no dup, ≤ top_k | ✅ | task5/6/7/9 |
| RRF `sum(1/(k+rank))`, rank từ 1, fuse 1 lần | ✅ | task7 + task9 |
| Fallback dùng cosine Dense, không dùng RRF score | ✅ | `dense[0]["score"]` |
| PageIndex/LLM lỗi không crash pipeline | ✅ | try/except ở task8/9/10 |
| Citation map về `sources` | ✅ | `sources: chunks` |
| Không hard-code API key | ✅ | `os.getenv()` / `.env` |

---

## 🎯 Chi Tiết 10 Mục

### Mục 1 — Chọn Đề Tài ✅
- [x] Chủ đề: **Pháp luật bất động sản** (Luật Nhà ở, Luật KD BĐS, Luật Bảo vệ NTD, Mẫu hợp đồng)
- [x] Phân công: Khanh (mục 3→5), Minh (mục 6→8), Hùng (mục 9)

### Mục 2 — Cài Môi Trường ✅
- [x] `.venv` + `pip install -e ".[dev]"` + playwright chromium
- [x] `.env` đã có (⚠️ không commit)

### Mục 3 — Thu Thập Dữ Liệu 🟡
**Legal — ✅ XONG (4 file)**
- [x] `luat-nha-o.pdf` (1.4 MB)
- [x] `luat-kinh-doanh-bds.pdf` (726 KB)
- [x] `luat_bao_ve_nguoi_tieu_dung_2023.pdf` (623 KB)
- [x] `mau-so-1a.docx` (35 KB)

**News — ❌ CHƯA LÀM**
- [ ] `ARTICLE_URLS` còn rỗng trong `task2_crawl_news.py`
- [ ] `crawl_article()` còn `NotImplementedError`
- [ ] Cần ≥5 file JSON với `{url, title, date_crawled, content_markdown}`

### Mục 4 — Chuẩn Hóa Markdown 🟡
- [x] `convert_legal_docs()` ✅ — 4/4 file chạy thành công
  - `luat-nha-o.md` (209K ký tự), `luat-kinh-doanh-bds.md` (145K), `luat_bao_ve_nguoi_tieu_dung_2023.md` (111K), `mau-so-1a.md` (53K)
- [x] `convert_news_articles()` ✅ — không crash khi news/ rỗng
- [ ] News: chờ Mục 3B

### Mục 5 — Chunk, Embedding & Index ✅
- [x] `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`, `EMBEDDING_MODEL="BAAI/bge-m3"`, `EMBEDDING_DIM=1024`
- [x] `load_documents()`, `chunk_documents()`, `embed_texts()`, `embed_chunks()`, `get_collection()`, `index_to_vectorstore()` — tất cả implement ✅
- [x] ID format `{path}::chunk-{i}`, upsert không nhân bản
- [x] Metadata.url đã điền URL chính phủ xác minh cho 3/4 file
- [x] 1392 chunk đã index vào ChromaDB (`chroma_db/`)
- [x] ✅ `test_chunk_documents_preserves_identity_and_metadata` PASS

### Mục 6 — Hybrid Retrieval ✅
**Dense Search (task5)**
- [x] `semantic_search(query, top_k)` → `list[SearchResult]`, `retrieval_method="dense"`
- [x] Dùng `embed_texts` từ task4 ✅, `score = 1.0 - distance`
- [x] ✅ contract test PASS

**Lexical Search (task6)**
- [x] `BM25Plus` (không phải BM25Okapi — tránh IDF âm)
- [x] `CORPUS` lazy-load, đọc qua `sys.modules` cho monkeypatch
- [x] Filter `score <= 0`, `retrieval_method="bm25"`
- [x] ✅ contract test PASS

**RRF Fusion (task7)**
- [x] `rerank_rrf(ranked_lists, top_k, k)`, `sum(1/(k+rank))`, rank từ 1
- [x] Deduplicate, sort giảm dần, `retrieval_method="hybrid"`
- [x] ✅ contract test PASS

### Mục 7 — Fallback & Retrieval Pipeline 🟡

**PageIndex Fallback (task8)**
- [x] Upload PDF từ `data/landing/legal/` lên PageIndex Cloud REST API
- [x] Cache `doc_id` vào `data/.pageindex_doc_ids.json`, idempotent
- [x] `pageindex_search()`: gọi Chat API, parse thành SearchResult, `score=1/(1+rank)`
- [x] Không có API key → trả `[]`, không crash
- [ ] ⚠️ `PAGEINDEX_API_KEY` chưa điền trong `.env` → fallback silently off

**Retrieval Pipeline (task9)**
- [x] `retrieve(query, top_k, score_threshold, use_reranking)` ✅
- [x] Dense + BM25 với `top_k * 2`, RRF fuse **đúng 1 lần**
- [x] Fallback dùng **`dense[0]["score"]`** (cosine gốc), không phải RRF score ✅
- [x] `except Exception: pass` — fallback lỗi trả hybrid ✅
- [x] `SCORE_THRESHOLD = 0.3` (chưa calibrate trên corpus thật)
- [x] ✅ 3/3 retrieve contract tests PASS

### Mục 8 — Generation Có Citation ✅
- [x] `reorder_for_llm()`: `front=chunks[::2]`, `back=chunks[1::2][::-1]`, non-mutating ✅
- [x] `format_context()`: `[Document N | Title: ... | Source: ...]` ✅
- [x] `call_llm()`: dispatch openai/gemini/anthropic theo `LLM_PROVIDER`
- [x] `generate_with_citation()`: safe refusal khi rỗng, catch LLM error ✅
- [x] ✅ contract test PASS

### Mục 9 — Chatbot & Evaluation 🟡

**Streamlit App (`app.py`)**
- [ ] ❌ Còn stub — `answer = "TODO: Itegration RAG Pipeline here"`, không gọi pipeline
- [ ] Cần wire: `generate_with_citation(query, top_k)` → hiển thị answer + sources + score

**Chatbot Độc Lập (`chatbot/`)**
- [x] Package `chatbot/` do Hùng implement — chạy qua `python -m chatbot.server`
- [x] Dùng TF-IDF hoặc fastembed (không phụ thuộc PyTorch), load corpus trực tiếp
- ⚠️ Không import từ `src/` — nhánh độc lập, không thay thế `app.py`

**Golden Dataset**
- [x] `group_project/evaluation/golden_dataset.json` — **20 câu** ✅ (acceptance test pass)
- [x] Schema đúng: `{question, expected_answer, expected_context}` ✅

**RAGAS Evaluation**
- [ ] ❌ `group_project/evaluation/run_evaluation.py` chưa chạy
- [ ] ❌ `group_project/evaluation/RESULT.md` còn **toàn bộ TODO** → acceptance test FAIL

### Mục 10 — Kiểm Tra & Nộp Bài ❌

**Tests**
- [x] `pytest tests/test_contracts.py -q` — **15/15 PASS** ✅
- [ ] `pytest tests/test_acceptance.py -q` — ❌ 3/5 FAIL (news + RESULT.md)
- [ ] `pytest -q` — ❌ chưa full pass

**Individual Reports**
- [ ] Khanh — chưa tạo file report
- [ ] Minh — chưa tạo file report
- [x] Hùng — `reports/2A202602942-HUNGLM.md` đã tạo nhưng **nội dung còn template trống**

**Final Checks**
- [ ] Kiểm tra không leak `.env` / API key / chroma_db cache trong repo
- [ ] Demo: 1 query trong domain + 1 query ngoài domain + A/B comparison

---

## 📊 Bảng Schema Tham Chiếu

| Kiểu | Cấu trúc |
|------|----------|
| **Document** | `{id, content, metadata:{source, title, doc_type:"legal"\|"news", url}}` |
| **Chunk** | `{id:"{doc_id}::chunk-{i}", content, metadata:{source, title, doc_type, url, chunk_index}}` |
| **SearchResult** | `{id, content, score:float, metadata, retrieval_method:"dense"\|"bm25"\|"hybrid"\|"pageindex"}` |
| **GenerationResult** | `{answer, sources:list[SearchResult], retrieval_source:"hybrid"\|"pageindex"\|"none"}` |

---

## 📊 Rubric 90 + 10 Bonus

| Tiêu chí | Điểm | Trạng thái |
|----------|------|---|
| Thu thập & chuẩn hoá (≥3 legal ✅ + ≥5 news ❌ + markdown ≥200 ký tự ✅) | 10 | 🟡 Thiếu news |
| Chunking, embedding, vector DB (ID ổn định, dim=1024) | 10 | ✅ Xong |
| Dense, BM25, RRF (score sort, no dup, hybrid mark) | 20 | ✅ Contract pass |
| Retrieval pipeline & fallback (threshold logic, 1x RRF) | 10 | ✅ Contract pass |
| Generation có citation & safe refusal | 15 | ✅ Contract pass |
| Chatbot UI end-to-end `app.py` (streamlit) | 10 | ❌ Còn stub |
| Golden dataset ≥15 câu ✅, 4 metric ❌, A/B ❌, error analysis ❌ | 10 | 🟡 Dataset xong / eval chưa chạy |
| README, reproducibility, báo cáo cá nhân, no `.env` leak | 5 | 🟡 Chưa hoàn thiện |
| **TỔNG** | **90** | **~55/90 khả năng đạt** |

**Bonus:**
- [ ] HyDE / query expansion có A/B (+3)
- [ ] Reranker nâng cao vs RRF (+3)
- [ ] Conversation memory (+2)
- [ ] Deploy online hoặc highlight citation (+2)

---

## 🔍 Lệnh Kiểm Tra Nhanh

```bash
# Contract test — 15/15 PASS ✅
pytest tests/test_contracts.py -q

# Acceptance test — 3/5 FAIL (news + RESULT.md)
pytest tests/test_acceptance.py -q

# Full
pytest -q

# Streamlit
streamlit run app.py

# PageIndex upload lần đầu (cần PAGEINDEX_API_KEY)
python -m src.task8_pageindex_vectorless
```

---

## ⚠️ Ghi Chú

- `bo-luat-dan-su.pdf` đã bị gỡ khỏi corpus — PDF scan ảnh, 0 ký tự convert được
- `SCORE_THRESHOLD=0.3` chưa calibrate trên corpus thật — chạy query in-domain và out-of-domain để đo
- `chatbot/` là nhánh độc lập của Hùng, không thay thế `app.py` theo spec
- `chroma_db/` đã có 1392 chunk — cần đảm bảo folder này trong `.gitignore`

---

**✏️ Cập nhật lần cuối:** 2026-09-21
