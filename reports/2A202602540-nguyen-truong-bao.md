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
   **Lý do/evidence:** Các trang `ielts.org` mang theo menu điều hướng lặp lại
   hàng trăm dòng; `article_01_how-ielts-is-scored.md` có khoảng 2/3 độ dài là
   danh sách link. Sau khi lọc, corpus giảm từ 753 xuống 402 chunk mà không mất
   nội dung thật (band scale, cách làm tròn, thời hạn 2 năm đều còn).
   **Trade-off:** Heuristic có thể loại nhầm chunk ngắn nhưng nhiều link hợp lệ,
   ví dụ danh sách tài nguyên ôn luyện ở cuối bài ieltsliz.

## Kiểm thử và kết quả

- Test đã dùng: `pytest tests/test_contracts.py -q` — trong đó
  `test_chunk_documents_preserves_identity_and_metadata`,
  `test_semantic_search_uses_shared_embedding_and_contract` và
  `test_lexical_search_returns_bm25_contract` là phần tôi phụ trách.
- Kết quả trước/sau: 753 → 402 chunk sau khi bật bộ lọc noise.
- Lỗi đã phát hiện và cách xử lý:
  - Chroma từ chối metadata giá trị `None` → convert `url=None` thành chuỗi rỗng
    ngay trước khi upsert, giữ nguyên `None` ở tầng Python để không phá contract.
  - `BM25Okapi` cho idf = 0 khi một term xuất hiện ở đúng 1 trong 2 document
    (N=2, freq=1 → `log(1.5) − log(1.5) = 0`), khiến filter `score <= 0` trả về
    rỗng và test contract fail. Sửa thành: chỉ loại chunk score 0 khi đã có ít
    nhất một match dương.

## Điều còn hạn chế

- Hạn chế cụ thể: `embed_texts()` với `sentence_transformers` load bge-m3
  (~2,3 GB) và chạy trên CPU, nên bước index 402 chunk mất vài phút và lần chạy
  đầu phụ thuộc vào tốc độ tải từ HuggingFace Hub.
- Nếu có thêm thời gian: cho phép chọn model embedding nhẹ hơn qua `.env` (ví dụ
  `all-MiniLM-L6-v2`) để vòng lặp thử nghiệm nhanh hơn, và đo A/B chất lượng
  retrieval giữa hai model thay vì mặc định chọn model lớn.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải
thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Nguyễn Trường Bảo
