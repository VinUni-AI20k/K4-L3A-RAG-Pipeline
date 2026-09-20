# Day 8 — RAG Pipeline

Chatbot RAG trả lời câu hỏi hỗ trợ khách hàng trên sàn thương mại điện tử:
chính sách trả hàng/hoàn tiền, phương thức thanh toán, quy định đăng bán và các
hướng dẫn thường gặp cho người mua.

## Nguồn dữ liệu

Trang chính sách và help center của các sàn TMĐT Việt Nam đều đứng sau WAF/Captcha
và cấm crawler trong `robots.txt`. Bài lab không cho phép vượt WAF, nên nhóm dựng
một **corpus synthetic**: 3 tài liệu chính sách (PDF, sinh bằng `fpdf2`) và 5 bài
hướng dẫn (JSON), tự soạn theo đúng cấu trúc và văn phong của tài liệu thật.

Toàn bộ nội dung corpus là do nhóm viết, **không phải trích dẫn nguyên văn từ
Shopee**. Nội dung nằm trong `src/task1_collect_legal_docs.py` và
`src/task2_crawl_news.py`; đổi sang nguồn thật chỉ cần thay phần dữ liệu ở hai
file đó, phần còn lại của pipeline giữ nguyên.

## Sản phẩm phải nộp

- Repository nhóm chạy được.
- Tối thiểu 3 tài liệu chính sách và 5 bài viết/page do nhóm tự thu thập.
- Pipeline: convert → chunk → index → dense + BM25 → RRF → fallback → generation có citation.
- Chatbot Streamlit hiển thị câu trả lời và nguồn đã dùng.
- Golden dataset tối thiểu 15 câu; đánh giá 4 metric và so sánh A/B.
- `group_project/evaluation/RESULT.md`.
- Mỗi thành viên nộp báo cáo cá nhân theo template trong `group_project/ịndividual/INDIVIDUAL_REPORT.md`.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
cp .env.example .env
```

Điền API key cần dùng trong `.env`; không commit file này.

> `crawl4ai` đã được chuyển sang extra `[crawl]` vì nó kéo theo toolchain Rust và
> fail khi cài trên khá nhiều máy. Pipeline không cần nó (corpus là synthetic).
> Ai muốn crawl nguồn thật: `pip install -e ".[crawl]"` rồi
> `python -m playwright install chromium`.

```bash
# 1. Thu thập và chuẩn hoá
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news
python -m src.task3_convert_markdown

# 2. Index và kiểm tra contract
python -m src.task4_chunking_indexing
pytest -q

# 3. Chạy sản phẩm
streamlit run app.py

# 4. Đánh giá và xuất RESULT.md
python -m group_project.evaluation.eval_pipeline
```

## Các lựa chọn kỹ thuật

| Hạng mục | Lựa chọn | Lý do |
| -------- | -------- | ----- |
| Chunking | `RecursiveCharacterTextSplitter`, size 500, overlap 50 | 500 ký tự (~100–150 từ) đủ chứa trọn một điều khoản; overlap 50 giữ câu bị cắt ở biên |
| Embedding | `paraphrase-multilingual-MiniLM-L12-v2` (384 chiều, local) | Nhẹ hơn `bge-m3` nhiều lần trên CPU nhưng vẫn hiểu tiếng Việt |
| Vector store | ChromaDB persistent, cosine | Chạy local, không cần dịch vụ ngoài |
| Lexical | BM25Okapi trên cùng bộ chunks | ID khớp với dense nên RRF fuse được theo ID |
| Fusion | RRF `k=60`, fuse đúng một lần | Gộp theo thứ hạng, không cộng thẳng cosine với BM25 |
| Fallback | PageIndex khi cosine dense < `SCORE_THRESHOLD` | Vectorless, tìm theo cây mục lục nên bù được khi dense lạc |
| Generation | DeepSeek `deepseek-chat` | Rẻ, nhanh, tương thích chuẩn OpenAI SDK |

### Vì sao không dùng `all-MiniLM-L6-v2`

Nhóm thử trước bằng `all-MiniLM-L6-v2` (model tiếng Anh) và phải loại. Đo trên
corpus này, nó chấm query **ngoài miền bằng tiếng Việt** tới 0.58–0.69, chồng lấn
hoàn toàn với query trong miền (0.63–0.84) — tức là nó đang nhận ra "đây là tiếng
Việt" chứ không hiểu nội dung, và không thể đặt threshold fallback ở đâu cả.

Bản multilingual tách được hai vùng:

| | dải cosine của chunk tốt nhất |
| --- | --- |
| 8 query in-domain | 0.360 – 0.791 |
| 8 query out-of-domain | 0.135 – 0.336 |

`SCORE_THRESHOLD=0.35` là điểm duy nhất nằm giữa. Biên chỉ rộng 0.024 (0.360 so
với 0.336), nên khi mở rộng corpus phải đo lại bằng nhiều query OOD hơn.

## Lưu ý quy tắc để có code quality tốt:

- Dense và BM25 nên cùng trả về `SearchResult` theo một schema.
- RRF chỉ nên dùng để gộp thứ hạng và chỉ chạy một lần.
- Fallback dùng cosine score gốc của dense retrieval.
- Threshold phải được hiệu chỉnh trên query in domain và out of domain, không có một con số đúng cho mọi corpus.

## Tài liệu

- [Module contracts](docs/MODULE_CONTRACTS.md): schema, interface và invariant mà code/test nên tuân theo.
- [Step-by-step guide](docs/STEP_BY_STEP.md): thứ tự triển khai và tiêu chí hoàn thành từng bước.
- [Grading rubric](docs/GRADING_RUBRIC.md): Rubric thang điểm.
- [Individual report](group_project/ịndividual/INDIVIDUAL_REPORT.md): template báo cáo cá nhân.
- [Suggested topics](docs/SUGGESTED_TOPICS.md): danh sách chủ đề tham khảo, không bắt buộc.

## Kiểm tra

```bash
# Contract tests
pytest tests/test_contracts.py -q

# Acceptance tests
pytest tests/test_acceptance.py -q

# Toàn bộ
pytest -q
```

## Khắc phục sự cố

**`UnicodeEncodeError` khi chạy `python -m src.taskN` trên Windows** — console
Windows mặc định là cp1252, không encode được tiếng Việt. `src/__init__.py` đã ép
`sys.stdout` sang UTF-8 nên trường hợp này đã được xử lý; nếu vẫn gặp ở script
nằm ngoài package `src`, chạy `set PYTHONIOENCODING=utf-8` trước.

**`400 Invalid n value` khi chạy evaluation** — Ragas mặc định gọi metric
`answer_relevancy` với `n=3`, nhưng DeepSeek và nhiều endpoint OpenAI-compatible
khác chỉ nhận `n=1`. `eval_pipeline.py` đã đặt `strictness=1` để tránh lỗi này.

**Đổi embedding model** — phải xoá `chroma_db/` rồi chạy lại
`python -m src.task4_chunking_indexing`, vì dimension và không gian vector không
tương thích ngược.
