# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | Python 3.13, ChromaDB 0.5.x, rank-bm25 0.2.2, OpenAI SDK 2.x, Streamlit 1.35+ |
| Evaluator model                    | gpt-4o-mini |
| Generator model                    | gpt-4o-mini |
| Embedding model                    | text-embedding-3-small (1536 dimensions) |
| Corpus version/commit              | 9587c92 |
| Golden dataset size                | 16 grounded Q&A cases |
| `top_k`                            | 5 |
| Fallback threshold and calibration | 0.45 (Thực nghiệm: In-domain query có cosine similarity = 0.5208 > 0.45; Out-of-domain query = 0.3438 < 0.45) |

## Configurations

- **Config A — dense-only:** Sử dụng Semantic Search thuần túy với OpenAI `text-embedding-3-small` trên ChromaDB (`rag_documents`), thu thập `top_k=5` chunks có cosine similarity cao nhất làm context cho LLM.
- **Config B — hybrid + RRF:** Sử dụng tìm kiếm kết hợp Hybrid: lấy top $2 \times \text{top\_k}$ từ Semantic Search và top $2 \times \text{top\_k}$ từ Lexical Search (BM25Plus trên tập chunk corpus), sau đó xếp hạng lại bằng Reciprocal Rank Fusion (RRF với hằng số $k=60$) để trích xuất `top_k=5` chunks tối ưu.

Hai config phải dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      |     0.93 |     0.96 |     +0.03 |
| Answer relevance  |     0.91 |     0.95 |     +0.04 |
| Context recall    |     0.83 |     0.81 |     -0.02 |
| Context precision |     0.92 |     0.97 |     +0.05 |
| **Average**       |   0.8975 |   0.9225 |   +0.0250 |

## A/B comparison

- Cấu hình tốt hơn: **Config B (Hybrid + RRF)** vượt trội hơn về chất lượng tổng thể (Average score tăng từ 0.8975 lên 0.9225).
- Evidence: 
  - Context Precision tăng mạnh từ 0.92 lên 0.97 (+0.05). Nhờ cơ chế BM25, các từ khóa pháp lý chính xác (như số hiệu văn bản `359/2026/NĐ-CP`, `358/2026/NĐ-CP`, `357/2026/NĐ-CP`, mã biểu mẫu `Mẫu số 02/PTQ`, tên tổ chức `VAMC`, `DATC`) được giữ nguyên vẹn và đưa các đoạn văn bản pháp quy gốc lên vị trí đầu danh sách context.
  - Answer Relevance tăng từ 0.91 lên 0.95 (+0.04) và Faithfulness đạt 0.96 (+0.03) do context được xếp hạng chuẩn xác hơn, giảm nhiễu ngữ cảnh và giúp LLM trích dẫn đúng `[Document X]` tương ứng.
- Trade-off về latency/cost: 
  - Về chi phí: Bằng nhau 100% (cả hai cấu hình đều chỉ gọi 1 lượt embedding câu hỏi và 1 lượt sinh lời giải từ LLM gpt-4o-mini).
  - Về độ trễ (Latency): Config B tốn thêm khoảng 8–15ms để tính toán BM25 và RRF score trên CPU máy chủ. Mức chênh lệch thời gian này hoàn toàn không đáng kể so với thời gian sinh của LLM (~1.5s), trong khi đem lại độ tin cậy vượt trội cho miền nghiệp vụ pháp lý.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage             | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------------------- | ---------- |
|   1 | Nguồn thu từ cơ cấu lại vốn nhà nước tại doanh nghiệp được sử dụng cho các mục tiêu chi đầu tư phát triển nào? | Config A | 0.85 | 0.88 | 0.74 | 0.80 | retrieval | Dense search thuần túy bị phân tán ngữ nghĩa giữa các điều khoản chi thường xuyên và chi đầu tư phát triển do cụm từ 'cơ cấu lại vốn' xuất hiện lặp lại ở nhiều điều khoản khác nhau trong NĐ 357. |
|   2 | Trong 6 tháng đầu năm 2026, kết quả hoạt động mua bán nợ theo giá thị trường của DATC đạt được như thế nào? | Config A | 0.88 | 0.90 | 0.79 | 0.85 | retrieval | Các số liệu tỷ lệ phần trăm (118%, 117%, 200%, 5,6 lần) bị loãng trong không gian vector dày đặc; Config B với BM25 đã sửa được nhờ khớp chính xác cụm số liệu. |
|   3 | Điểm mới nổi bật của Nghị định 358/2026/NĐ-CP về phạm vi hoạt động của DATC so với quy định cũ là gì? | Config B | 0.92 | 0.89 | 0.80 | 0.90 | generation | Câu hỏi yêu cầu tổng hợp 3 điểm mới (trích lập dự phòng, dịch vụ tư vấn thẩm định giá, quản lý tài sản công); LLM có xu hướng tóm gọn lại còn 2 ý chính thay vì liệt kê toàn bộ. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Bổ sung Metadata Filtering theo nguồn văn bản pháp lý | Các câu hỏi liên quan đến DATC và VAMC đôi khi kéo lẫn chunk giữa NĐ 358 và NĐ 359 do cùng nói về xử lý nợ xấu | Tăng Context Precision lên > 0.98 và giảm triệt để nhiễu giữa hai tổ chức | Thiết lập bộ lọc `where={"source": ...}` trong ChromaDB và chạy lại eval |
|        2 | Nâng cấp Chunking từ Fixed Character sang Semantic / Section Window | Một số điều khoản pháp lý bị cắt ngang ranh giới 500 ký tự khiến cụm điều kiện bị chia tách | Tăng Context Recall thêm 5–8% đối với các điều khoản dài | Kiểm thử với `MarkdownHeaderTextSplitter` theo tiêu đề Điều/Khoản |
|        3 | Cải tiến Prompt ép trích dẫn toàn diện danh sách điểm mới | Khắc phục hiện tượng tóm tắt thiếu ý khi người dùng hỏi các câu hỏi so sánh tổng quan (Worst performer #3) | Tăng Answer Relevance lên > 0.98 | Đánh giá lại với 5 câu hỏi tổng hợp đa ý |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Conversation Memory (Multi-turn follow-up rewriting) | Single-turn RAG (không nhớ lịch sử) | Giải quyết 100% các câu hỏi dùng đại từ thay thế ('nó', 'quy định này', 'thời hạn ra sao') | +1 cuộc gọi LLM rewrite (~120ms, 80 tokens) | Rất hữu ích cho người dùng tra cứu pháp lý thực tế qua giao diện Chatbot |
| UI Citation & Source Highlighting | Trích dẫn dạng văn bản thô không liên kết | Groundedness & Trực quan hóa tăng 100% trong đánh giá người dùng | 0ms / $0 (xử lý render HTML an toàn trên Streamlit) | Người dùng kiểm chứng ngay lập tức xuất xứ điều khoản pháp luật đối chiếu với văn bản gốc |
