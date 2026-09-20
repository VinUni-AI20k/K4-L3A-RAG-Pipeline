# Tổng kết dự án: K4-L3A-RAG-Pipeline

Chatbot RAG hỗ trợ khách hàng sàn thương mại điện tử. File này ghi lại những gì
đã làm và **những gì chưa làm**, để người đọc không phải suy đoán.

Số liệu đánh giá không nằm ở đây — chúng nằm trong
[`group_project/evaluation/RESULT.md`](group_project/evaluation/RESULT.md), do
`eval_pipeline.py` sinh ra từ lần chạy thật.

## 1. Dữ liệu (Task 1, 2, 3)

- Corpus **synthetic**: 3 tài liệu chính sách (PDF, sinh bằng `fpdf2`) và 5 bài
  hướng dẫn (JSON). Lý do: help center của sàn TMĐT chặn crawler bằng WAF/Captcha
  và bài lab không cho phép vượt WAF.
- Nội dung do nhóm tự soạn theo cấu trúc tài liệu thật, **không trích dẫn nguyên
  văn từ Shopee**. README và docstring của Task 1/2 đều ghi rõ điều này.
- Task 3 convert PDF bằng `markitdown`, JSON render thủ công kèm metadata header.
  MarkItDown trích text từ PDF chèn khoảng trắng đôi giữa các từ nên có bước gom
  lại một space trước khi ghi.

## 2. Chunking & Indexing (Task 4)

- `RecursiveCharacterTextSplitter`, `chunk_size=500`, `chunk_overlap=50` → 16 chunks.
- Embedding: **`paraphrase-multilingual-MiniLM-L12-v2`** (384 chiều, chạy local).
- Đã thử `all-MiniLM-L6-v2` trước và **phải loại**: model tiếng Anh chấm query
  ngoài miền bằng tiếng Việt tới 0.58–0.69, chồng lấn hoàn toàn với query trong
  miền (0.63–0.84), khiến không thể đặt ngưỡng fallback. Chi tiết trong README.
- Lưu vào ChromaDB persistent, cosine distance. ID chunk sinh từ đường dẫn tương
  đối (`legal/payment-methods-shopee.md::chunk-0`) nên chạy lại pipeline là
  upsert đè, không sinh bản trùng.

## 3. Retrieval (Task 5, 6, 7, 8)

- **Semantic (Task 5):** query đi qua đúng `embed_texts()` của Task 4 nên index
  và query luôn cùng model, cùng dimension.
- **Lexical (Task 6):** BM25Okapi trên cùng bộ chunks, nên ID khớp với dense.
- **RRF (Task 7):** fuse theo `id`, không theo `content` — `chunk_overlap` làm
  nhiều chunk có đoạn text trùng nhau, fuse theo content sẽ nuốt mất kết quả.
- **Fallback (Task 8):** gọi PageIndex API thật, có timeout và cache doc ID.
  **Chưa chạy được end-to-end** vì nhóm chưa có `PAGEINDEX_API_KEY`. Khi thiếu
  key hoặc khi provider lỗi, hàm trả về danh sách rỗng và Task 9 quay lại dùng
  hybrid result — không có nhánh nào sinh nội dung giả.

## 4. Pipeline & Generation (Task 9, 10)

- `retrieve()`: dense + BM25 → RRF một lần → so ngưỡng với **cosine score gốc
  của dense**, không so với RRF score (hai thang đo khác nhau).
- `SCORE_THRESHOLD = 0.35`, hiệu chỉnh bằng 8 query in-domain (0.360–0.791) và
  8 query out-of-domain (0.135–0.336). Biên chỉ rộng 0.024 — mở rộng corpus thì
  phải đo lại.
- **Generation (Task 10):** DeepSeek `deepseek-chat`. Có lost-in-the-middle
  reordering, context kèm title + source để citation `[Document N]` đối chiếu
  được, và safe refusal khi không retrieve được gì hoặc provider lỗi.

## 5. UI và đánh giá

- **Streamlit (`app.py`):** hiển thị câu trả lời kèm panel nguồn (title, file,
  loại tài liệu, chunk index, score, retrieval method).
- **Evaluation:** golden dataset 15 cặp Q&A, mỗi case kèm đoạn văn gốc trong
  `expected_context`. Đo 4 metric Ragas (Faithfulness, Answer Relevancy, Context
  Recall, Context Precision) và so sánh A/B giữa dense-only và hybrid + RRF.
- `eval_pipeline.py` hỗ trợ cả Ragas 0.1.x và 0.4.x, và **không có nhánh sinh
  điểm giả**: thiếu API key thì script dừng và báo lỗi.

## 6. Kiểm thử

`pytest -q` → 20/20 pass (15 contract tests + 5 acceptance tests), chạy trên
Python 3.12, không gọi network.

## 7. Những chỗ còn hạn chế

- Corpus là synthetic và rất nhỏ (8 tài liệu, 16 chunks). Mọi con số đánh giá
  chỉ nói lên pipeline chạy đúng, không nói lên nó tốt trên dữ liệu thật.
- PageIndex fallback chưa được kiểm chứng end-to-end (thiếu API key).
- Biên threshold giữa in-domain và out-of-domain chỉ 0.024, quá hẹp để tin cậy
  trên corpus lớn hơn.
- Phần Recommendations trong `RESULT.md` cần người đọc bảng Worst performers rồi
  điền tay; script chỉ sinh được số liệu, không sinh được kết luận.
- Chưa làm phần bonus (HyDE/query expansion, cross-encoder reranker,
  conversation memory, deploy online).
