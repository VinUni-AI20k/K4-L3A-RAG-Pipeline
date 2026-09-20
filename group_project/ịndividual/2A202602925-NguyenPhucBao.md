# Individual contribution report

---

## Thông tin

- Họ và tên: Nguyễn Phúc Bảo
- Mã học viên: 2A202602925
- Nhóm: ScoutX
- Repository/branch: `PhucBao1/K4-L3A-RAG-Pipeline-ScoutX` — `feat/data-indexing`, `fix/task6-task8-runtime-bugs`, `chore/add-run-eval-script`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 1-3: thu thập & chuẩn hoá dữ liệu | Tải 4 văn bản luật hiện hành từ chinhphu.vn (kiểm tra hiệu lực từng văn bản), crawl 6 bài báo; phát hiện PDF ký số là ảnh scan, chuyển sang dùng bản DOC/DOCX song song | PR #1 `feat/data-indexing` | Done |
| Task 4: chunk + embed + index | RecursiveCharacterTextSplitter (500/50), dispatch embedding theo `EMBEDDING_PROVIDER`, index ChromaDB | PR #1, `src/task4_chunking_indexing.py` | Done |
| Review & fix Dũng | Đọc code `task6`/`task8`, phát hiện 2 bug runtime (BM25 `CORPUS` rỗng ngoài test, thiếu `import json`), fix và verify trước/sau | PR #3 `fix/task6-task8-runtime-bugs` | Done |
| Evaluation | Review 15 câu golden dataset có căn cứ từ corpus thật, script `run_eval.py` (ragas: faithfulness/answer relevance/context recall/precision), điền `RESULT.md` với phân tích 3 worst-case có root cause | `group_project/evaluation/` | Done |
| Bonus: HyDE + LLM reranker | Implement 2 kỹ thuật retrieval nâng cao, benchmark thật so với RRF trên toàn bộ 15 câu | `src/bonus_advanced_retrieval.py`, `run_eval_bonus.py`, nhánh `chore/add-run-eval-script` | Done |
| Bonus: UI citation highlight + conversation memory | Tô màu citation khớp nguồn, viết lại câu hỏi follow-up bằng lịch sử hội thoại trước khi retrieve | `app.py`, `task10_generation.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng bản DOC/DOCX (Công báo Chính phủ phát hành song song) thay vì OCR trên PDF ký số.
   **Lý do/evidence:** PDF là ảnh scan, `pdfminer` extract ra rỗng. Test OCR bằng tesseract cho sai số liệu thật ("16"→"l6", "11"→"1]") — rủi ro với văn bản luật.
   **Trade-off:** Phải giữ cả 2 loại file, thêm dependency LibreOffice để convert `.doc` cũ.

2. **Quyết định:** Thêm HyDE (sinh câu trả lời giả định rồi embed) cho dense retrieval.
   **Lý do/evidence:** Fix hoàn toàn 1 case tệ nhất đã xác định qua phân tích root cause — context recall đi từ 0.0 lên 1.0 trên cùng câu hỏi.
   **Trade-off:** Thêm 1 lượt gọi LLM mỗi query (latency + chi phí).

## Kiểm thử và kết quả

- Test: `pytest tests/` — 20/20 pass xuyên suốt các thay đổi.
- Kết quả trước/sau: BM25 runtime — `lexical_search()` từ `[]` (bug) → trả kết quả thật; Hybrid+RRF trung bình 0.761 vs Dense-only 0.729; HyDE 0.808, LLM reranker 0.825 (cao nhất).
- Lỗi đã phát hiện: BM25 `CORPUS` không populate ngoài test; thiếu `import json` ở task8;

## Điều còn hạn chế

- PageIndex fallback đúng contract, có test, nhưng chưa chạy live (không có API key thật).
- BM25 chưa lọc từ hành chính lặp lại trong văn bản luật dài. Nếu có thêm thời gian sẽ làm trước tiên vì ảnh hưởng trực tiếp tới 1 trong 3 worst performer.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Nguyễn Phúc Bảo
