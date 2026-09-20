# Chatbot pháp lý - Hợp đồng mua bán căn hộ (mục 9)

Ứng dụng độc lập với `src/task1..task10` (những file đó vẫn giữ nguyên dạng
bài tập chưa hoàn thiện). Package `chatbot/` tự làm toàn bộ pipeline
ingest → chunk → embed → hybrid retrieval (dense + BM25 + RRF) → sinh câu
trả lời có trích dẫn, phục vụ riêng cho mục 9 (chatbot UI + evaluation).

## Vì sao không dùng Streamlit / sentence-transformers

- UI là **một trang HTML tĩnh** (`chatbot/static/index.html`, thuần
  HTML/CSS/JS, không cần build) thay vì `streamlit run app.py`, phục vụ bởi
  một server Python nhỏ dùng `http.server` có sẵn trong thư viện chuẩn.
- Máy đang chạy có **chính sách Application Control chặn DLL của PyTorch**
  (`torch_python.dll` bị chặn), nên `sentence-transformers` không tải được.
  Phần dense retrieval dùng `fastembed` (chạy trên ONNX Runtime, không cần
  PyTorch) với model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
  Nếu chạy trên máy khác không bị chặn, có thể đổi lại sang
  `sentence-transformers` bằng cách sửa `chatbot/engine.py`.

## Kho dữ liệu

Đã chuyển 3/4 tài liệu trong `data/landing/legal/` sang Markdown tại
`data/standardized/legal/`:

- `luat-nha-o.md`, `luat-kinh-doanh-bds.md`, `mau-so-1a.md` — có text layer, convert thành công.
- `bo-luat-dan-su.pdf` — **bị bỏ qua**: đây là bản scan (ảnh), không có text
  layer và máy này không có Tesseract OCR để trích xuất. Nếu cần đưa vào
  corpus, hãy OCR file này riêng (hoặc thay bằng bản PDF có text) rồi chạy
  lại chatbot - nó sẽ tự convert file mới xuất hiện trong `data/landing/legal/`.

Chunk được tách theo từng "Điều N." (article-aware chunking) thay vì cắt
theo số ký tự cố định, để mỗi đoạn trích dẫn là một điều luật trọn vẹn.

## Chạy chatbot

```bash
# Trong venv của repo (đã có sẵn các dependency cần thiết)
python -m pip install -e ".[dev]"   # lần đầu, để cài fastembed/markitdown[docx]
cp .env.example .env                # điền LLM_PROVIDER + API key tương ứng
python -m chatbot.server
```

Server in ra URL (mặc định `http://127.0.0.1:8000`) và tự mở trình duyệt.
Lần chạy đầu sẽ tải model embedding (~100-500MB, cache tại `chatbot/.cache/`
và thư mục cache của `fastembed`) nên có thể mất một lúc; các lần sau khởi
động nhanh vì embedding được cache theo fingerprint của corpus.

Nếu chưa điền API key cho `LLM_PROVIDER` trong `.env`, chatbot vẫn chạy và
vẫn trả về **các đoạn trích dẫn liên quan tìm được** (phần retrieval hoạt
động độc lập với LLM), chỉ phần câu trả lời tổng hợp sẽ báo lỗi rõ ràng
thay vì crash.

## Đánh giá (evaluation)

- `group_project/evaluation/golden_dataset.json`: 20 câu hỏi - đáp án chuẩn,
  bám sát nội dung thật của `luat-nha-o.md`, `luat-kinh-doanh-bds.md`,
  `mau-so-1a.md` (điều kiện hợp đồng, công chứng, thanh toán theo tiến độ,
  bảo lãnh, bảo hành, phạt vi phạm, chuyển nhượng hợp đồng, giải quyết
  tranh chấp...).
- `group_project/evaluation/run_evaluation.py`: chạy toàn bộ golden set qua
  2 cấu hình (`use_hybrid=False` - dense-only, `use_hybrid=True` - hybrid+RRF),
  chấm bằng ragas (`faithfulness`, `answer_relevancy`, `context_recall`,
  `context_precision`), rồi ghi kết quả vào `eval_raw_results.json` và
  render lại `group_project/evaluation/RESULT.md`.

```bash
python group_project/evaluation/run_evaluation.py
```

Script này **luôn dùng OpenAI (`OPENAI_API_KEY`) làm giám khảo ragas**
(ragas 0.4 cần một LLM kiểu instructor + embeddings; `openai` là SDK duy
nhất trong dependencies của repo mà ragas hỗ trợ sẵn qua `llm_factory`),
bất kể `LLM_PROVIDER` của chatbot là gì. Cần có `OPENAI_API_KEY` trong
`.env` để chạy được bước này.
