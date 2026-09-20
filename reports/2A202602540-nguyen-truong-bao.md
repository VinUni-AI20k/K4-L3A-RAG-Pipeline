# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Trường Bảo
- Mã học viên: 2A202602540
- Nhóm: 4ae
- Repository/branch: `K4-L3A-RAG-Pipeline` / `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Chunking | Recursive splitter 500/50, ID ổn định `<doc>::chunk-<n>`, `chunk_index` liên tục sau khi lọc | `src/task4_chunking_indexing.py` | Done |
| Lọc navigation noise | Heuristic mật độ markdown link để loại chunk chỉ chứa menu điều hướng | `src/task4_chunking_indexing.py` | Done |
| Embedding | `embed_texts()` dispatch theo `EMBEDDING_PROVIDER` (sentence_transformers / openai / gemini), cache model trong process | `src/task4_chunking_indexing.py` | Done |
| Vector store | Chroma persistent collection cosine, upsert theo batch 256, sanitize metadata `None` | `src/task4_chunking_indexing.py` | Done |
| Dense search | `semantic_search` dùng chung `embed_texts()`, đổi cosine distance sang similarity, khử trùng ID | `src/task5_semantic_search.py` | Done |
| BM25 | `lexical_search` trên đúng corpus chunks nạp lại từ Chroma, tokenizer `\w+` unicode, cache index | `src/task6_lexical_search.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** BM25 nạp corpus từ chính Chroma collection thay vì đọc lại Markdown.
   **Lý do/evidence:** Nếu BM25 tự chunk lại từ file, ID và `chunk_index` sẽ
   lệch với dense, và RRF ở Task 7 gộp theo `id` sẽ coi cùng một đoạn văn là hai
   document khác nhau — fusion mất hết tác dụng khử trùng.
   **Trade-off:** BM25 phụ thuộc vào việc đã chạy `task4` trước; đổi lại hai
   nhánh retrieval được bảo đảm nhìn vào cùng một tập chunk.

2. **Quyết định:** Lọc chunk có mật độ markdown link > 50% (và ≥ 3 link) trước khi embed.
   **Lý do/evidence:** Dữ liệu crawl từ Wikipedia, Wikivoyage và cổng Cục Du
   lịch Quốc gia có nhiều menu, mục lục và liên kết điều hướng. Task 3 hiện đã
   đổi link Markdown thành anchor text trước khi Task 4 chạy, nên phép đo trên
   corpus chuẩn hóa hiện tại cho kết quả 2.633 → 2.633 chunk (không có chunk nào
   bị loại). Heuristic vẫn được giữ như lớp phòng vệ khi nhóm bổ sung Markdown
   chưa qua bước làm sạch hoặc thay đổi nguồn crawl trong tương lai.
   **Trade-off:** Bộ lọc không cải thiện kích thước corpus hiện tại và có thể
   loại nhầm một chunk ngắn chứa danh sách liên kết tài nguyên du lịch hợp lệ;
   đổi lại nó ngăn navigation noise đi vào embedding nếu dữ liệu đầu vào thay đổi.

## Kiểm thử và kết quả

- Test đã dùng: `pytest tests/test_contracts.py -q` — trong đó
  `test_chunk_documents_preserves_identity_and_metadata`,
  `test_semantic_search_uses_shared_embedding_and_contract` và
  `test_lexical_search_returns_bm25_contract` là phần tôi phụ trách.
- Kết quả trên corpus du lịch hiện tại: 12 tài liệu chuẩn hóa tạo 2.633 chunk;
  trước/sau bộ lọc noise đều là 2.633 chunk, ID không trùng và độ dài tối đa 500
  ký tự. Nguyên nhân bộ lọc không loại thêm dữ liệu là Task 3 đã làm sạch cú pháp
  link ở tầng `data/standardized/`.
- Lỗi đã phát hiện và cách xử lý:
  - Chroma từ chối metadata giá trị `None` → convert `url=None` thành chuỗi rỗng
    ngay trước khi upsert, giữ nguyên `None` ở tầng Python để không phá contract.
  - `BM25Okapi` cho idf = 0 khi một term xuất hiện ở đúng 1 trong 2 document
    (N=2, freq=1 → `log(1.5) − log(1.5) = 0`), khiến filter `score <= 0` trả về
    rỗng và test contract fail. Sửa thành: chỉ loại chunk score 0 khi đã có ít
    nhất một match dương.

## Điều còn hạn chế

- Hạn chế cụ thể: `embed_texts()` với `sentence_transformers` load bge-m3
  (~2,3 GB) và chạy trên CPU, nên bước index 2.633 chunk có thể mất nhiều phút;
  lần chạy đầu còn phụ thuộc vào tốc độ tải từ HuggingFace Hub.
- Nếu có thêm thời gian: đo A/B `BAAI/bge-m3` với một model multilingual nhẹ
  hơn trên cùng golden dataset, đồng thời thử chunking theo cấu trúc Điều/Khoản
  cho tài liệu pháp lý thay vì chỉ chia theo số ký tự.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải
thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Nguyễn Trường Bảo
