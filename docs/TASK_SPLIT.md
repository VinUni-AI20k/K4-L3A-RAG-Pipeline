# Phân công công việc — Day 8 RAG Pipeline

**Đề tài:** Dịch vụ đại học — Học bổng & Hỗ trợ tài chính (VinUniversity)
**Nhóm trưởng:** Nguyễn Long Khánh

---

## Dữ liệu

Đã có sẵn 8 file markdown về học bổng/hỗ trợ tài chính VinUni (cào từ `admissions.vinuni.edu.vn` hôm trước), để sẵn ở `data/standardized/legal/` làm điểm khởi đầu.

**Còn thiếu — người phụ trách Task 1–2 cần bổ sung:**

| Yêu cầu | Trạng thái | Việc cần làm |
|---|---|---|
| Task 1: ≥3 tài liệu **PDF/DOCX** chính sách | Chưa đủ | 8 file hiện có là cào từ trang web (HTML → markdown), không phải file PDF/DOCX gốc. Cần tìm thêm bản PDF chính thức (VD "Quy chế học bổng", "Sổ tay sinh viên") — hoặc cả nhóm thống nhất dùng 8 trang web này làm nguồn "legal" và báo lại với giảng viên để chắc chắn được chấp nhận. |
| Task 2: ≥5 bài **news** (tin tức/thông báo) | Chưa có | 8 file hiện có đều là trang policy/FAQ tĩnh, không phải "news". Cần crawl mới: tin/thông báo học bổng theo đợt, phỏng vấn sinh viên nhận học bổng, v.v. |
| Task 3: convert sang markdown chuẩn | Cần xử lý thêm | 8 file hiện có dùng front-matter kiểu khác (`audience`, `department`...) so với schema Day 8 (`source/title/doc_type/url`). Người làm Task 3/4 cần quyết định giữ hay bỏ phần front-matter này khi viết `load_documents()`. |

---

## Phân công 3 người

| # | Phụ trách | Module | Điểm rubric | Việc cụ thể |
|---|---|---|---:|---|
| 1 | **Data & Indexing** | Task 1, 2, 3, 4 | 20đ | Tìm PDF/DOCX chính sách thật, crawl ≥5 bài news, convert markdown, chunk + embed + index vào ChromaDB |
| 2 | **Retrieval** | Task 5, 6, 7, 8, 9 | 30đ | Dense search, BM25, RRF, PageIndex fallback (optional), ráp retrieval pipeline + hiệu chỉnh threshold |
| 3 | **Generation & Product** | Task 10, `app.py`, Evaluation | 35đ | Generation kèm citation, chatbot Streamlit, 15 câu golden Q&A + RAGAS 4 metric + A/B, điền `RESULT.md` |

Phần README + individual reports (5đ) là việc chung — nhóm trưởng tổng hợp và review tích hợp giữa 3 phần.

---

## Ràng buộc kỹ thuật chung (đọc trước khi code)

- Mọi module trả đúng schema trong `src/contracts.py` (`Document`, `SearchResult`, `GenerationResult`)
- `id` phải ổn định, không trùng; chạy lại pipeline không tạo dữ liệu trùng
- Task 4 và Task 5 phải dùng chung hàm `embed_texts()`
- Fallback so sánh với **cosine score gốc của dense search**, không dùng RRF score
- Không commit `.env` hoặc API key thật
- Chi tiết đầy đủ: `docs/MODULE_CONTRACTS.md`, `docs/STEP_BY_STEP.md`, `docs/GRADING_RUBRIC.md`
