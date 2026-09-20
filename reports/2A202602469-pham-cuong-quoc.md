# Individual contribution report

## Thông tin

- Họ và tên: Phạm Cường Quốc
- Mã học viên: 2A202602469
- Nhóm: 4ae
- Repository/branch: `K4-L3A-RAG-Pipeline` / `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| RRF fusion | `rerank_rrf`: gộp theo thứ hạng, khử trùng theo `id`, đánh dấu `hybrid`, không cộng trực tiếp cosine với BM25 score | `src/task7_reranking.py` | Done |
| PageIndex fallback | Wrapper có cache document ID, render Markdown → PDF tạm bằng fpdf2, timeout chờ retrieval, trả `[]` khi thiếu API key | `src/task8_pageindex_vectorless.py` | Done |
| Retrieval pipeline | `retrieve`: chạy dense + BM25, RRF đúng một lần, so threshold với cosine gốc, nuốt lỗi provider để không crash | `src/task9_retrieval_pipeline.py` | Done |
| Generation có citation | Reorder chống lost-in-the-middle, context gắn nhãn title/source, safe refusal, retry backoff cho 429/500/503 | `src/task10_generation.py` | Done |
| Cấu hình provider | Chuẩn hoá `.env` (Gemini), dispatch 3 provider trong `call_llm` | `.env.example`, `src/task10_generation.py` | Done |
| Tích hợp & README | Ráp toàn pipeline chạy end-to-end, viết README kiến trúc và quyết định thiết kế | `README.md` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Ngưỡng fallback so với **cosine score gốc của dense**, không so với RRF score.
   **Lý do/evidence:** RRF score chỉ là tổng nghịch đảo thứ hạng; với hai ranked
   list và `k=60`, hạng 1 chỉ đạt khoảng `1/61 + 1/62 ≈ 0,033`. Nếu đem so với
   `SCORE_THRESHOLD=0.3` thì **mọi** truy vấn đều rơi xuống fallback, kể cả khi
   dense đang rất tự tin. Hai contract test
   `test_retrieve_uses_dense_score_for_fallback` và
   `test_retrieve_fuses_once_when_dense_is_confident` khoá đúng hành vi này.
   **Trade-off:** Phải giữ lại danh sách dense nguyên bản song song với danh
   sách đã fuse, tốn thêm bộ nhớ và làm hàm `retrieve` dài hơn.

2. **Quyết định:** Lỗi PageIndex bị nuốt và trả về kết quả hybrid, thay vì raise.
   **Lý do/evidence:** PageIndex là dịch vụ ngoài và nhóm không có
   `PAGEINDEX_API_KEY`; nếu để lỗi lan ra thì mọi câu hỏi có dense score thấp sẽ
   làm sập chatbot thay vì trả lời kém hơn một chút. Hành vi này được khoá bằng
   `test_retrieve_survives_fallback_provider_error`.
   **Trade-off:** Lỗi cấu hình thật (API key sai) bị che thành "fallback không
   có kết quả"; tôi bù lại bằng cách in cảnh báo ra stdout thay vì im lặng.

## Kiểm thử và kết quả

- Test đã dùng: `pytest tests/test_contracts.py -q`, tập trung vào 4 test của
  Task 7 và Task 9 (RRF, fallback, fuse-once, provider lỗi).
- Lỗi đã phát hiện và cách xử lý:
  - `LLM_PROVIDER=openai` trong `.env` nhưng chỉ có `GEMINI_API_KEY` → chuyển
    sang Gemini.
  - `gemini-2.5-flash` trả 404 "no longer available to new users" và
    `gemini-flash-latest` trả 503 UNAVAILABLE → cố định `gemini-3.6-flash` và
    thêm retry có backoff cho 429/500/503 trong `call_llm`.
  - `generate_with_citation` có thể trả `retrieval_source="dense"` khi chạy với
    `use_reranking=False`, vi phạm `validate_generation_result` (chỉ chấp nhận
    hybrid/pageindex/none) → map về `hybrid`.

## Điều còn hạn chế

- Hạn chế cụ thể: PageIndex fallback chưa chạy end-to-end vì không có
  `PAGEINDEX_API_KEY`; nhánh này mới chỉ được xác minh bằng contract test
  (bao gồm test provider lỗi), chưa có số liệu thật trên corpus của nhóm.
- `SCORE_THRESHOLD` đã được hiệu chỉnh trên corpus du lịch: đo best cosine của
  dense trên 9 câu in-domain (0,564–0,760) và 7 câu out-of-domain (0,394–0,553)
  rồi chốt `0.56` tại điểm tách hai phân phối. Hạn chế là biên rất mỏng (~0,011)
  và câu in-domain thấp nhất ("Sa Pa thuộc tỉnh nào") gần sát ngưỡng; nếu có
  thêm thời gian tôi sẽ mở rộng tập hiệu chỉnh lên vài chục câu mỗi phía và chọn
  ngưỡng theo phân vị thay vì theo min/max.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải
thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Phạm Cường Quốc
