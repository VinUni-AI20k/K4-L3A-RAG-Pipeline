## 1. Chọn đề tài

- Chọn một chủ đề trong [danh sách gợi ý](SUGGESTED_TOPICS.md) hoặc chủ đề khác.
- Phân công role, chia nhiệm vụ các thành viên
- Mỗi thành viên ghi lại commit mình phụ trách để hoàn thiện individual report

## 2. Cài môi trường

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m playwright install chromium
cp .env.example .env
```

## 3. Thu thập dữ liệu

- Tải tối thiểu 3 PDF/DOCX vào `data/landing/legal/`.
- Crawl tối thiểu 5 bài vào `data/landing/news/`.
- Mỗi JSON có `url`, `title`, `date_crawled`, `content_markdown`.

```bash
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news
```

Trong repo có setup sẵn Crawl4AI, các bạn tùy ý sử dụng công cụ khác của mình

### Dữ liệu nhóm: Vật lí 10–12 (Kết nối tri thức với cuộc sống)

- Ba PDF sách giáo khoa đã được đặt thủ công trong `data/landing/legal/`. Tên thư mục `legal` là tên cũ của bộ khung; ở đề tài này các file là sách giáo khoa, không phải văn bản pháp luật. Task 1 kiểm tra sự hiện diện và định dạng PDF.
- Năm trang Vật lí công khai được thu thập riêng vào `data/landing/news/article_01.json` đến `article_05.json` bằng Task 2. JSON lưu URL, tiêu đề, thời điểm thu thập, phần mở đầu của trang và thông tin giấy phép. Chúng là nguồn bổ sung, không phải bản sao của năm bài đã gộp trong PDF.
- Danh mục và tình trạng nguồn nằm tại `data/landing/SOURCES.md`. Các PDF là ảnh scan, nên cần OCR và kiểm tra công thức ở bước 4 trước khi tạo Markdown.

## 4. Chuẩn hóa Markdown

Hoàn thiện Task 3 rồi chạy:

```bash
python -m src.task3_convert_markdown
```

Với corpus Vật lí của nhóm, ba PDF là ảnh scan nên Task 3 dùng `pdfplumber` và Tesseract OCR tiếng Việt; chỉ dùng lớp chữ PDF khi có thể trích xuất. Đầu ra `data/standardized/legal/*.md` có metadata sách và mốc `PDF page` để truy nguồn. Năm JSON được chuyển sang `data/standardized/news/*.md`, giữ URL, thời điểm thu thập và giấy phép.

Trên Windows, cần Tesseract và mô hình `vie.traineddata` trong `.cache/tessdata/` (hoặc đặt `TESSERACT_CMD` và `TESSDATA_DIR`). Có thể cài và tải mô hình từ [tessdata_fast chính thức](https://github.com/tesseract-ocr/tessdata_fast/blob/main/vie.traineddata):

```powershell
winget install --id UB-Mannheim.TesseractOCR --exact --accept-package-agreements --accept-source-agreements
New-Item -ItemType Directory -Path .cache\tessdata -Force
Invoke-WebRequest -Uri https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/vie.traineddata -OutFile .cache\tessdata\vie.traineddata
.\.venv\Scripts\python.exe -m src.task3_convert_markdown
```

Kiểm tra thủ công một số trang của mỗi sách, đặc biệt là công thức, bảng và dấu tiếng Việt vì OCR không đảm bảo chính xác tuyệt đối.

## 5. Chunk, embedding và index

Task 4 đọc 8 file Markdown trong `data/standardized/`, chia recursive chunk
500 ký tự (overlap 50), tạo embedding bằng OpenAI `text-embedding-3-small`
rồi upsert vào ChromaDB tại `chroma_db/` (cosine distance). ID chunk ổn định nên chạy lại
không tạo bản ghi trùng. Bước này cần `OPENAI_API_KEY` và phát sinh chi phí embedding.

```bash
python -m src.task4_chunking_indexing
```

Trên Windows dùng `\.venv\Scripts\python.exe -m src.task4_chunking_indexing`.
Sau khi chạy, kiểm tra số bản ghi bằng:

```powershell
.\.venv\Scripts\python.exe -c "from src.task4_chunking_indexing import get_collection; print(get_collection().count())"
```

Không commit `chroma_db/` hoặc API key. Dùng cùng `EMBEDDING_MODEL` khi
index và khi truy vấn; đổi model thì cần tạo lại index. Nếu đã có index từ
`BAAI/bge-m3`, cần xóa/rebuild collection trước khi chạy demo vì kích thước
vector đã thay đổi.

## 6. Xây dựng hybrid retrieval

- Task 5: semantic search từ ChromaDB.
- Task 6: BM25L trên cùng corpus chunks, token hóa Unicode cho tiếng Việt.
- Task 7: RRF gộp hai bảng xếp hạng theo ID.

Chạy bước 5 trước và kiểm tra ChromaDB đã có dữ liệu. Task 5 dùng lại
`EMBEDDING_MODEL` để mã hóa câu hỏi và cần `OPENAI_API_KEY`; Task 6 và Task 7
không gọi API embedding.
Task 6 đọc Markdown đã chuẩn hóa và tái tạo cùng các chunk, không cần tải
model. Task 7 kết hợp kết quả của Task 5 và 6; RRF không phải LLM reranker.

```bash
python -m src.task5_semantic_search
python -m src.task6_lexical_search
python -m src.task7_reranking
```

Về rerank là không bắt buộc, các bận có thể sử dụng Jina, hoặc tự self host BGE (hoặc không làm)

## 7. Hoàn thiện fallback và retrieval pipeline

- Task 8 trả `retrieval_method="pageindex"`.
- Task 9 chỉ chạy RRF một lần.
- Calibrate threshold bằng query đúng domain và query ngoài domain.
- Dùng dense cosine score gốc để quyết định fallback.

Chạy pipeline local trước (không cần LLM API key):

```powershell
.\.venv\Scripts\python.exe -m src.task9_retrieval_pipeline
```

Ngưỡng mặc định `SCORE_THRESHOLD=0.62` chỉ là điểm khởi đầu: trên index hiện
tại, 15 câu golden có top-1 dense score `0.632–0.803`; 3 câu ngoài lĩnh vực
đạt `0.413–0.478`, còn 4 câu hỏi về giá sách/học phí/tác giả/lịch thi đạt
`0.543–0.607`. Khoảng cách ở ranh giới rất nhỏ, nên cần đo lại khi thay
corpus hoặc embedding model và không coi ngưỡng là bằng chứng đã có đáp án.

PageIndex Cloud là tùy chọn và cần `PAGEINDEX_API_KEY`. Chỉ sau khi có quyền
đưa tài liệu lên dịch vụ ngoài, điền key vào `.env` và **chủ động** chạy:

```powershell
.\.venv\Scripts\python.exe -m src.task8_pageindex_vectorless
```

Task 8 upload 3 PDF SGK gốc và tạo 5 PDF chữ tạm từ bài viết Markdown;
`pageindex_doc_ids.json` và `pageindex_pdfs/` được ignore. Chờ PageIndex xử
lý xong trước khi thử fallback. Truy vấn thông thường không tự upload. Nếu
không có key, chưa upload hoặc dịch vụ lỗi, Task 9 giữ kết quả hybrid thay vì
crash. Mỗi lần fallback chỉ thử tối đa 3 tài liệu, ưu tiên nguồn khớp BM25.

## 8. Generation có citation

Hoàn thiện Task 10:

- Reorder chunks nhưng không làm mất ID.
- Context có title/source.
- Dispatch theo `LLM_PROVIDER`: OpenAI, Gemini hoặc Anthropic Claude.
- Không đủ evidence thì trả safe refusal.

```bash
python -m src.task10_generation
```

**Hoàn thành khi:** answer đúng `GenerationResult` và citation map được về `sources`.

## 9. Chatbot và evaluation

```bash
streamlit run app.py
```

- UI hiển thị answer, source, retrieval method và score.
- Tạo ít nhất 15 golden Q&A dựa trên corpus.
- Chạy 4 metric: faithfulness, answer relevance, context recall, context precision.
- So sánh dense-only với hybrid + RRF trên cùng cấu hình còn lại.
- Điền `group_project/evaluation/RESULT.md`.

Có thể chạy evaluation tái lập bằng:

```powershell
.\.venv\Scripts\python.exe -m src.task11_evaluation
```

Kết quả chi tiết được lưu ở `group_project/evaluation/evaluation_runs.json`;
báo cáo tổng hợp nằm trong `RESULT.md`. Bộ evaluator hiện là lexical,
deterministic (không phải Ragas judge model), nên cần ghi rõ khi thuyết trình.

**Hoàn thành khi:** chatbot chạy end-to-end và báo cáo không còn placeholder.

## 10. Kiểm tra và nộp bài

```bash
pytest tests/test_contracts.py -q
pytest tests/test_acceptance.py -q
pytest -q
```

- Mỗi thành viên hoàn thiện individual report.
- Kiểm tra repository không chứa `.env`, API key hoặc file cache.
- Demo một query đúng, một query ngoài domain và kết quả A/B.
