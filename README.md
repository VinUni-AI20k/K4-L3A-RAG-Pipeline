# Hệ thống RAG Tra cứu Pháp lý & Tái cơ cấu Doanh nghiệp Nhà nước

> **Dự án thực hành Day 8 — RAG Pipeline**  
> **Lớp:** K4-L3A  
> **Nhóm thực hiện:** Phronesis  
> **Repository:** `https://github.com/nthanhwork/K4-L3A-RAG-Pipeline`

---

## 1. Giới thiệu đề tài

Dự án xây dựng hệ thống **Trợ lý Trí tuệ Nhân tạo (RAG Chatbot)** chuyên sâu phục vụ tra cứu, phân tích và giải đáp các chính sách quy định pháp luật mới nhất của Chính phủ Việt Nam ban hành trong tháng 09/2026 về lĩnh vực tài chính, ngân hàng, xử lý nợ xấu và tái cơ cấu vốn nhà nước tại doanh nghiệp.

### Phạm vi dữ liệu thu thập và chuẩn hóa:
- **Tài liệu pháp quy gốc (PDF/DOCX):**
  1. **Nghị định số 359/2026/NĐ-CP** (17/09/2026): Quy định về thành lập, tổ chức hoạt động và cơ chế tài chính của Công ty Quản lý tài sản của các tổ chức tín dụng Việt Nam (**VAMC**) — vốn điều lệ 5.000 tỷ đồng, phương thức mua nợ thị trường và trái phiếu đặc biệt, nghiệp vụ xử lý nợ.
  2. **Nghị định số 358/2026/NĐ-CP** (15/09/2026): Quy định cơ chế hoạt động và quản lý tài chính của Công ty Mua bán nợ Việt Nam (**DATC**) — 7 nhóm ngành nghề kinh doanh, nguyên tắc trích lập dự phòng, điều kiện hỗ trợ phục hồi doanh nghiệp.
  3. **Nghị định số 357/2026/NĐ-CP** (15/09/2026): Quy định quản lý, sử dụng nguồn thu từ cơ cấu lại vốn nhà nước tại doanh nghiệp — phân cấp nộp ngân sách Trung ương/Địa phương, chi đầu tư phát triển, chi phí tinh giản biên chế, biểu mẫu Mẫu số 02/PTQ.
- **Tài liệu báo chí nghiệp vụ (JSON & Markdown):**
  - 5 bài phân tích chuyên sâu từ các cơ quan báo chí chính thống (Báo Nhân Dân, Báo Đấu Thầu, TTXVN BNews, VOV) về kết quả hoạt động thực tế 6 tháng đầu năm 2026 và tác động chính sách của các văn bản trên.

---

## 2. Thành viên nhóm & Phân công nhiệm vụ

| STT | Thành viên | Mã học viên | Vai trò phụ trách | Module & Deliverables chính |
| :---: | :--- | :---: | :--- | :--- |
| 1 | **Ngọ Doãn Ngọc** | `2A202602635` | **Retrieval & Reranking** | Task 5 (Dense Semantic Search), Task 6 (BM25 Lexical Search), Task 7 (Reciprocal Rank Fusion RRF), Task 8 (PageIndex Fallback), Task 9 (Retrieval Pipeline & Fallback Threshold Calibration). |
| 2 | **Nguyễn Thái Anh** | `2A202602810` | **Generation & UI** | Task 10 (Generation kèm trích dẫn nguồn `[Document X]`, Reordering chống Lost-in-the-middle, Safe Refusal), Xây dựng giao diện Streamlit UI (`app.py`), tính năng Bonus Citation Highlighting & Conversation Memory. |
| 3 | **Hoàng Ngọc Đăng Khoa** | `2A202602790` | **Evaluation & Benchmark** | Biên soạn và nghiệm thu Golden Dataset 16 cases (`golden_dataset.json`), phát triển script đo kiểm tự động (`run_eval.py`), thực hiện đánh giá A/B Testing 4 metrics RAG trong `RESULT.md`, phân tích lỗi (Failure Analysis) và nghiệm thu 20/20 unit tests. |

---

## 3. Kiến trúc Pipeline & Tính năng nổi bật

Pipeline tuân thủ đầy đủ chuẩn giao tiếp dữ liệu trong [`docs/MODULE_CONTRACTS.md`](docs/MODULE_CONTRACTS.md):

```
[Dữ liệu chuẩn hóa MD] 
       │
       ▼ (Task 4: Chunking & Indexing - Recursive Splitter)
[ChromaDB (Dense)]  +  [Corpus In-Memory (BM25Okapi)]
       │                              │
       ▼ (Task 5: Dense Search)       ▼ (Task 6: Lexical Search)
 [Top 2k Dense Results]        [Top 2k Sparse Results]
       │                              │
       └──────────────┬───────────────┘
                      ▼ (Task 7: Reranking)
           [Reciprocal Rank Fusion (RRF, k=60)]
                      │
                      ▼ (Task 9: Fallback Decision)
            Cosine Score < 0.45 ?
                 ├── Yes ──► [Task 8: PageIndex Vectorless Fallback]
                 └── No  ──► [Top k Hybrid Chunks]
                      │
                      ▼ (Task 10: Generation & Context Reorder)
               [LLM Prompting with Citations]
                      │
                      ▼
        [Chatbot UI: Answer + Sources + Citation Highlighting]
```

### Điểm nhấn kỹ thuật & Tính năng Bonus (+4 điểm):
1. **Hybrid Search với RRF Reranking:** Kết hợp ưu điểm ngữ nghĩa của Dense Vector với khả năng bắt chính xác số hiệu văn bản pháp lý của BM25.
2. **Conversation Memory (+2 điểm Bonus):** Khả năng ghi nhớ ngữ cảnh đa lượt thoại thông qua kỹ thuật Query Rewriting cho các câu hỏi nối tiếp.
3. **Citation & Source Highlighting (+2 điểm Bonus):** Tự động bóc tách các tag `[Document X]` trong câu trả lời thành các badge nổi bật tương tác được trên giao diện Streamlit, kèm thẻ nguồn trích dẫn đối chiếu nguyên văn.
4. **Cơ chế Safe Refusal an toàn:** Trả về thông báo từ chối chuẩn mực khi câu hỏi nằm ngoài phạm vi tài liệu hoặc thiếu căn cứ pháp lý.

---

## 4. Bảng kết quả đánh giá A/B Testing (Evaluation)

Hệ thống được đánh giá thực nghiệm trên **16 grounded cases** trong [`group_project/evaluation/golden_dataset.json`](group_project/evaluation/golden_dataset.json):

| Metric | Config A (Dense-only) | Config B (Hybrid + RRF) | Delta (B − A) | Nhận xét |
| :--- | :---: | :---: | :---: | :--- |
| **Faithfulness** | 0.93 | **0.96** | **+0.03** | Giảm thiểu ảo giác, câu trả lời bám sát context |
| **Answer Relevance** | 0.91 | **0.95** | **+0.04** | Trả lời trúng trọng tâm câu hỏi nghiệp vụ |
| **Context Recall** | 0.83 | 0.81 | -0.02 | Độ bao phủ thông tin chuẩn xác |
| **Context Precision** | 0.92 | **0.97** | **+0.05** | **Vượt trội**: Chunk liên quan nhất được đẩy lên đầu |
| **Điểm trung bình** | **0.8975** | **0.9225** | **+0.0250** | **Cấu hình Hybrid + RRF chiến thắng** |

Chi tiết xem tại: [`group_project/evaluation/RESULT.md`](group_project/evaluation/RESULT.md).

---

## 5. Hướng dẫn cài đặt và chạy thử nghiệm (Quick Start)

### 5.1. Khởi tạo môi trường
```bash
python -m venv .venv
# Kích hoạt môi trường ảo:
source .venv/bin/activate       # Trên Linux/macOS
.venv\Scripts\activate          # Trên Windows

# Cài đặt thư viện dependencies:
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
python -m playwright install chromium

# Cấu hình file môi trường:
cp .env.example .env
```
*Lưu ý: Điền các API Key cần thiết (`OPENAI_API_KEY`, `GEMINI_API_KEY`, v.v.) vào file `.env`.*

### 5.2. Chạy pipeline dữ liệu & indexing
```bash
# 1. Chuẩn hóa dữ liệu sang Markdown
python -m src.task3_convert_markdown

# 2. Thực hiện Chunking, Embedding và nạp vào ChromaDB
python -m src.task4_chunking_indexing
```

### 5.3. Khởi chạy giao diện Chatbot Streamlit
```bash
streamlit run app.py
```

### 5.4. Chạy script đánh giá tự động
```bash
python group_project/evaluation/run_eval.py
```

---

## 6. Kiểm tra và Nghiệm thu (Testing)

Dự án tích hợp đầy đủ test suite kiểm định hợp đồng dữ liệu và tiêu chí nghiệm thu:

```bash
# Chạy toàn bộ kiểm thử kỹ thuật:
pytest -q
```
**Kết quả nghiệm thu:** `20 passed in 9.90s` (15 contract tests + 5 acceptance tests đạt 100%).

---

## 7. Cấu trúc thư mục dự án

```text
K4-L3A-RAG-Pipeline/
├── app.py                             # Ứng dụng Streamlit UI kèm Citation Highlighting & Memory
├── chroma_db/                         # Cơ sở dữ liệu vector ChromaDB
├── data/
│   ├── landing/                       # Dữ liệu thô thu thập ban đầu (PDF pháp luật, JSON bài báo)
│   └── standardized/                  # Dữ liệu chuẩn hóa định dạng Markdown (legal/, news/)
├── docs/                              # Tài liệu rubric, contract và hướng dẫn kỹ thuật
├── group_project/
│   ├── evaluation/
│   │   ├── golden_dataset.json        # 16 câu hỏi - đáp chuẩn hóa (Ground Truth)
│   │   ├── HANDOVER.md                # Tài liệu bàn giao giữa các vai trò
│   │   ├── RESULT.md                  # Báo cáo đánh giá chi tiết 4 metrics & so sánh A/B
│   │   └── run_eval.py                # Script chạy benchmark tự động
│   └── individual/                    # Báo cáo đóng góp cá nhân từng thành viên
├── reports/                           # Báo cáo cá nhân và kết quả nộp bài
│   ├── 2A202602635_NgoDoanNgoc.md
│   ├── 2A202602790_HoangNgocDangKhoa.md
│   ├── 2A202602810-NguyenThaiAnh.md
│   └── RESULT.md
├── src/                               # 10 Tasks pipeline từ thu thập đến generation
└── tests/                             # Unit tests: test_contracts.py và test_acceptance.py
```
