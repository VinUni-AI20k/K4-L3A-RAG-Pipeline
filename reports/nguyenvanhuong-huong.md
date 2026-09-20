# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Văn Hưởng
- Mã học viên: (điền)
- Nhóm: DuoH (K4-DAY08)
- Repository/branch: https://github.com/lechihung252/K4-DAY08-DuoH — `main`, nhánh `feature/rag-pipeline`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 1 — thu thập tài liệu chính sách | Tải 5 PDF chính thức từ CDN ielts.org (band descriptors, key assessment criteria, scores guide, sample tasks AC/GT), ghi manifest `sources.json` với URL nguồn | `src/task1_collect_legal_docs.py`, commit `191c09e` | Done |
| Task 3 — chuẩn hoá Markdown | Hai đường convert: pdfplumber parse theo toạ độ cho PDF band descriptors dạng bảng 4 cột không viền (MarkItDown trộn cột); MarkItDown cho PDF văn xuôi; news JSON → Markdown. Output có front matter `source/title/doc_type/url` | `src/task3_convert_markdown.py`, commit `7b5ccc5` | Done |
| Task 4 — chunking & indexing | RecursiveCharacterTextSplitter 500/50, embed bge-m3 (batch 32, hỗ trợ `EMBEDDING_PROVIDER` sentence_transformers/openai/gemini), index ChromaDB cosine theo batch 100, ID `doc_type/file.md::chunk-N` | `src/task4_chunking_indexing.py`, commit `724b328` | Done |
| Task 5 — semantic search | `semantic_search`: đổi cosine distance → similarity clamp [0, 1], dedupe ID, sort giảm dần, trả `retrieval_method="dense"` đúng contract | `src/task5_semantic_search.py`, PR #1 (`97317c0`) | Done |
| Task 10 — generation có citation | Prompt chỉ trả lời từ Context; `reorder_for_llm` đặt chunk rank cao ở hai đầu; `format_context` kèm ID/title/source; dispatch OpenAI/Gemini/Anthropic theo `LLM_PROVIDER`; kiểm tra citation phải map về `sources`, sai thì safe refusal | `src/task10_generation.py`, PR #1 (`97317c0`) | Done |
| Test offline Task 5/10 | 8 test monkeypatch: sort/dedupe/convert cosine, giữ ID và thứ tự, refusal khi citation lạ/không citation/provider lỗi, gắn `retrieval_source="pageindex"`, dispatch 3 provider không cần mạng | `tests/test_task5_task10.py`, `97317c0` | Done |
| Chatbot Streamlit | Chat UI nối `generate_with_citation`, slider `top_k`, expander hiển thị từng nguồn với citation ID, file, phương thức truy hồi và score | `app.py`, commit `98f3679` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Parse PDF band descriptors bằng pdfplumber theo toạ độ ô thay vì MarkItDown.
   **Lý do/evidence:** Bảng 4 cột (Task Achievement / Coherence / Lexical / Grammar) không kẻ viền, MarkItDown ghép các cột thành đoạn vô nghĩa nên chunk không thể trả lời câu "Band N yêu cầu gì ở tiêu chí X". Parse theo toạ độ cho ra mỗi ô (band × tiêu chí) thành một mục `### <criterion>` dưới heading `## Writing Task N — Band M`.
   **Trade-off:** Code phụ thuộc layout của đúng file PDF này; đổi phiên bản PDF phải chỉnh lại toạ độ. Heading band nằm ở chunk đầu nên các chunk sau của cùng band mất thông tin band (nguyên nhân chính của 4 refusal trong evaluation).

2. **Quyết định:** Safe refusal được quyết định bằng kiểm tra citation sau khi sinh, không tin vào LLM tự từ chối.
   **Lý do/evidence:** Contract yêu cầu mọi citation phải map về `sources`. Nếu LLM không cite hoặc cite ID không có trong context, coi như không có bằng chứng và trả `SAFE_REFUSAL` với `sources=[]`, `retrieval_source="none"`. Test `test_generation_refuses_uncited_or_unknown_sources` khoá hành vi này.
   **Trade-off:** Nghiêm ngặt nên bị refusal giả khi LLM viết citation lệch format (`[chunk_id: ...]`, thiếu tiền tố `news/`); nhóm đã bổ sung `normalize_citations` ở bước evaluation để chấp nhận hậu tố khớp duy nhất.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: `pytest tests/test_task5_task10.py -q` (8 passed), `pytest tests/test_contracts.py -q`; chạy `streamlit run app.py` với query in-domain ("How many words for Task 2?") và out-of-domain ("What is the capital of Brazil?").
- Kết quả trước/sau nếu có: Trước khi parse pdfplumber, file `ielts-writing-band-descriptors.md` là văn bản trộn cột không dùng được; sau khi sửa được 23.669 ký tự có cấu trúc band × tiêu chí, index ra 985 chunks. Evaluation nhóm: faithfulness Config B = 1.000 trên 14 câu có trả lời, tức mọi câu trả lời sinh ra đều bám context.
- Lỗi đã phát hiện và cách xử lý: Chroma trả distance có thể vượt [0, 1] nhẹ do sai số float → clamp; kết quả query có thể trùng ID khi collection có bản ghi lặp → dedupe trong `semantic_search`.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: chunk 500 ký tự cắt rời heading band khỏi nội dung tiêu chí, khiến retrieval không phân biệt Band 5/7/8 (worst performer #1 trong RESULT.md).
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: chunk band descriptors theo đơn vị band × tiêu chí và prepend heading cha vào `content` mỗi chunk, giữ nguyên ID để không phá contract.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Nguyễn Văn Hưởng
