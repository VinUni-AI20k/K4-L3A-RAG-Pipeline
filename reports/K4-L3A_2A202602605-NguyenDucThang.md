# Individual contribution report

---

## Thông tin

- Họ và tên: Nguyễn Đức Thắng
- Mã học viên: 2A202602605
- Nhóm: K4-L3A-RAG-Pipeline
- Repository/branch: https://github.com/thangws4/K4-Day08-GICUNGDC — branch `main`, `thangnd`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
| --- | --- | --- | --- |
| Task 1 — Thu thập văn bản pháp luật | Khai `SOURCES` 6 văn bản từ Công báo, viết hàm bóc link PDF từ trang văn bản, kiểm tra text layer và dấu "Xem tiếp Công báo", ghi manifest nguồn | `src/task1_collect_legal_docs.py`, `data/landing/legal/sources.json`, commit `14319eb`, `6aa4710`, `5b89001` | Done |
| Task 2 — Crawl tin bài | 5 URL baochinhphu.vn, giới hạn crawl vào selector thân bài, từ chối bài dưới 500 ký tự | `src/task2_crawl_news.py`, `data/landing/news/article_01..05.json` | Done |
| Task 3 — Chuẩn hóa Markdown | MarkItDown + bỏ header Công báo lặp mỗi trang + nối dòng bị PDF ngắt giữa câu; header metadata để truy ngược về file landing và URL gốc | `src/task3_convert_markdown.py`, `data/standardized/**` | Done |
| Task 4 — Chunk, embed, index | `load_documents` đọc metadata từ header thay vì suy từ tên file; cắt theo ranh giới `Điều` và gắn lại tiêu đề điều cha; bge-m3 + ChromaDB cosine; dọn chunk không còn nguồn | `src/task4_chunking_indexing.py`, commit `eb4e015` | Done |
| Chatbot UI | `app.py` hoàn chỉnh: hiển thị answer, nguồn, điểm số kèm tên thang đo, retrieval method, safe refusal, không sập khi provider lỗi; kèm design system | `app.py`, `assets/design-system.css`, `assets/citation.js`, `.streamlit/config.toml`, commit `1780a28` | Done |
| Golden dataset | Dựng lại 17 case bằng script trích nguyên văn đoạn văn bản từ corpus, thêm 3 case out-of-domain | `group_project/evaluation/golden_dataset.json`, `golden_dataset_out_of_domain.json` | Done |
| Script evaluation | Viết `run_evaluation.py` chạy A/B dense-only vs hybrid+RRF trên 4 metric RAGAS, kèm hàm hiệu chỉnh threshold | `src/run_evaluation.py` | Done |
| Sửa lỗi Task 9, Task 10 | Task 10: giữ reference client Gemini; Task 9: đọc `SCORE_THRESHOLD` từ `.env` thay vì hard-code | `src/task10_generation.py`, `src/task9_retrieval_pipeline.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Thay toàn bộ PDF "signed" trên datafiles.chinhphu.vn bằng bản đăng Công báo, và tải đủ mọi phần của mỗi văn bản.
   **Lý do/evidence:** pdfplumber trích được **0 ký tự** từ 4/5 file ban đầu vì đó là bản scan ảnh — convert nguyên trạng sẽ cho Markdown rỗng, RAG không có gì để retrieve. Sau khi đổi nguồn lại phát hiện văn bản bị cắt: Luật 36/2024/QH15 có 89 điều nhưng file phần 1 chỉ tới **Điều 23**, kết thúc bằng dòng "(Xem tiếp Công báo số 979 + 980)". Corpus sau khi sửa: 6 văn bản, 11 file, đều có text layer, dung lượng giảm từ 175 MB xuống 20 MB.
   **Trade-off:** Mất bản có chữ ký số; phải bóc link từ HTML trang Công báo nên sẽ hỏng nếu trang đổi layout; một văn bản bị chia thành nhiều file nên citation phải ghi kèm "phần k/n".

2. **Quyết định:** Cắt chunk theo ranh giới `Điều` và gắn lại tiêu đề điều cha vào đầu mỗi chunk.
   **Lý do/evidence:** Câu hỏi "mức phạt nồng độ cồn với ô tô", chunk retrieve được chứa đúng khoản phạt nhưng bắt đầu giữa câu, mất mệnh đề "đối với người điều khiển **xe ô tô**" nằm ở chunk trước, nên LLM từ chối trả lời. Nguy hiểm hơn: chunk cũ đưa ra mức **6–8 triệu** vốn là mức của xe mô tô, trong khi mức đúng cho ô tô là **18–20 triệu** (Điều 6 khoản 9 NĐ 168/2024). Sau khi sửa, 89% chunk mang theo tiêu đề điều luật và hệ thống trả lời đúng 18–20 triệu kèm citation.
   **Trade-off:** Số chunk tăng 4.245 → 4.937 (+16%), thời gian embed và dung lượng index tăng tương ứng; tiêu đề lặp lại làm loãng một phần tín hiệu embedding của thân chunk; mỗi lần đổi chiến lược chunk phải index lại khoảng 45 phút trên CPU.

## Kiểm thử và kết quả

- **Test hoặc query tôi đã dùng:** `pytest -q` (20 passed). Smoke test pipeline thật: `semantic_search`, `lexical_search`, `retrieve`, `generate_with_citation`. `AppTest` headless cho `app.py`. Test escaping với payload `<img src=x onerror=alert(1)>` và URL `javascript:` cho thẻ nguồn. Đo độ trễ từng chặng và hiệu chỉnh threshold trên 17 câu in-domain + 3 câu out-of-domain.
- **Kết quả trước/sau:** corpus legal từ 4/5 file 0 ký tự thành 6 văn bản đều có text; Luật 36 phủ từ Điều 23 lên Điều 89; tin bài từ 10.471 xuống 3.016 ký tự mỗi bài sau khi bỏ menu và footer; chunk mang tiêu đề điều luật từ 0% lên 89%; câu hỏi nồng độ cồn ô tô từ "bot từ chối" thành trả lời đúng 18–20 triệu có citation; độ trễ mỗi câu từ 12 giây xuống 1,4 giây sau khi đổi sang `gemini-3.5-flash-lite`.
- **Lỗi đã phát hiện và cách xử lý:** (1) PDF scan không có text layer, đổi nguồn và thêm cảnh báo tự động khi tải. (2) Văn bản bị cắt theo số Công báo, tải đủ phần và thêm guard phát hiện dòng "Xem tiếp". (3) `genai.Client()` làm biến tạm bị garbage collect trước khi request gửi đi gây `RuntimeError: client has been closed`, sửa bằng giữ reference. (4) `print` tiếng Việt crash trên console cp1252, reconfigure stdout UTF-8. (5) `SCORE_THRESHOLD` khai trong `.env` nhưng không dòng code nào đọc, sửa Task 9 đọc từ env có xử lý giá trị rỗng và sai định dạng. (6) Ngưỡng 0.3 không tách được in-domain và out-of-domain, đo lại và quét toàn dải để chọn 0.60.

## Điều còn hạn chế

- **Một hạn chế cụ thể của phần tôi làm:** Corpus thiếu Nghị định 238/2026/NĐ-CP và 236/2026/NĐ-CP, là hai văn bản mà chính tin bài trong corpus dẫn chiếu 7 lượt. Câu hỏi về quy định có hiệu lực từ 2026 sẽ được trả lời dựa trên bản chưa sửa đổi, hoặc sinh mâu thuẫn giữa nhánh tin bài và nhánh văn bản luật.
- **Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện:** Bổ sung hai nghị định đó rồi đo lại context recall. Sau đó thay cách gắn tiêu đề điều luật: hiện đang lặp text vào thân chunk, nên chuyển sang lưu số điều trong metadata và chỉ ghép lại lúc format context, để không làm loãng embedding.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Nguyễn Đức Thắng
