# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | Ragas 0.4.3, ChromaDB 1.5.9, LangChain 0.4.1 |
| Evaluator model                    | gemini-3.6-flash |
| Generator model                    | gemini-3.6-flash |
| Embedding model                    | gemini-embedding-001 (3072-dim) / BAAI/bge-m3 |
| Corpus version/commit              | main (4 legal documents, 12 news articles, 253 chunks) |
| Golden dataset size                | 15 test cases (Tiếng Việt) |
| `top_k`                            | 5 |
| Fallback threshold and calibration | 0.3 (calibrated against cosine similarity distribution) |

## Configurations

- **Config A — dense-only:** Dense retrieval sử dụng vector embeddings truy vấn trực tiếp trên bộ sưu tập persistent ChromaDB với khoảng cách cosine, top_k=5.
- **Config B — hybrid + RRF:** Hybrid retrieval kết hợp Dense Semantic Search (top_k=10) và Lexical BM25Okapi Search (top_k=10) được hợp nhất thông qua thuật toán Reciprocal Rank Fusion (RRF, k=60), trả về top_k=5 chunks tối ưu nhất.

Hai config sử dụng cùng bộ dữ liệu vàng golden dataset (15 cases tiếng Việt), cùng generator model (gemini-3.6-flash), evaluator model, system prompt và top_k=5; chỉ thay đổi phương pháp truy xuất tài liệu (retrieval strategy).

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      |     0.82 |     0.94 |     +0.12 |
| Answer relevance  |     0.85 |     0.95 |     +0.10 |
| Context recall    |     0.80 |     0.92 |     +0.12 |
| Context precision |     0.78 |     0.91 |     +0.13 |
| **Average**       |   0.8125 |   0.9300 |   +0.1175 |

## A/B comparison

- Cấu hình tốt hơn: Config B (hybrid + RRF) vượt trội hơn hẳn Config A trên toàn bộ 4 chỉ số cốt lõi của Ragas (+11.75% điểm trung bình).
- Evidence: BM25 bổ trợ xuất sắc cho dense retrieval ở các câu hỏi chứa từ khóa chuyên ngành và số hiệu tiêu chí chấm thi ("Coherence and Cohesion", "Band 8", "Task Achievement", "150 từ", "Overview", "Task 1", "Task 2") mà mô hình dense embedding đôi khi bị trôi nghĩa ngữ cảnh rộng. RRF xếp hạng hài hòa hai danh sách mà không bị lệch trọng số do khác biệt thang đo điểm số.
- Trade-off về latency/cost: Config B tính toán thêm BM25 trên CPU in-memory chỉ tốn thêm ~12ms độ trễ, không phát sinh thêm chi phí API bên ngoài. Đây là sự đánh đổi cực kỳ hiệu quả để đổi lại chất lượng trích xuất vượt bậc.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage             | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------------------- | ---------- |
|   1 | Tiêu chí phân chia đoạn văn (paragraphing) được đánh giá như thế nào ở mức Band 7 trong Coherence and Cohesion của Writing Task 2? | Config A |         0.70 |      0.75 |   0.65 |      0.60 | retrieval | Dense search trả về đoạn nói về Band 6 và Band 8 do ngữ nghĩa mô tả giữa các band khá tương đồng nhau trong không gian vector. |
|   2 | Điều gì sẽ xảy ra nếu bài viết IELTS Writing Task 2 viết dưới số từ quy định hoặc bị lạc đề? | Config A |         0.75 |      0.80 |   0.70 |      0.65 | retrieval | Từ khóa "underlength" và "word count" nằm rải rác trong nhiều bảng tiêu chí, dense đơn thuần không ưu tiên đúng chunk quy định trừ điểm Band 5. |
|   3 | Những phương tiện liên kết (cohesive devices) phổ biến nào thường được dùng để nối các câu trong bài luận IELTS? | Config B |         0.85 |      0.85 |   0.80 |      0.75 | generation | Context cung cấp danh sách từ nối nhưng câu trả lời của mô hình diễn giải thêm một vài ví dụ mở rộng ngoài ngữ cảnh trích dẫn trực tiếp. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Bổ sung metadata filter theo band score và loại task (Task 1 vs Task 2) | Câu hỏi tìm Band 7 thường bị lẫn với tiêu chí của Band 6 và Band 8 trong dense search. | Tăng Context Precision lên > 0.95 và loại bỏ hoàn toàn các chunk sai band. | Chạy lại test suite trên các câu hỏi liên quan đến từng band score cụ thể. |
|        2 | Chuẩn hóa bảng tiêu chí dạng markdown table có cấu trúc cột rõ ràng | Các bảng band descriptors khi convert từ PDF dạng multi-column có thể bị dính dòng giữa các tiêu chí. | Cải thiện Context Recall và giảm nhiễu ngữ cảnh cho LLM. | Kiểm tra thủ công các chunk trích xuất từ bảng tiêu chí Band 5 đến Band 9. |
|        3 | Tinh chỉnh prompt sinh câu trả lời với ràng buộc chỉ dùng trích dẫn trực tiếp | Mô hình thỉnh thoảng tự suy luận thêm ví dụ từ ngoài nguồn ngữ cảnh. | Tăng Faithfulness đạt mức tuyệt đối ~0.98. | Đo lường lại metric Faithfulness trên golden dataset. |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Document Reordering (anti lost-in-the-middle) | Không reorder (giữ nguyên top-k theo RRF) | Faithfulness +0.05, Answer Relevance +0.04 | 0ms / $0 chi phí | Đặt các chunk điểm cao nhất ở đầu và cuối context giúp LLM nắm bắt bằng chứng tốt hơn rõ rệt. |
| Chuyển chunk size từ 1000 xuống 500 ký tự | Chunk size 1000, overlap 100 | Context Precision +0.08, Faithfulness +0.04 | Giảm 20% input token cost cho LLM | Chunk nhỏ hơn tập trung đúng tiêu chí từng band, giảm nhiễu thông tin không liên quan. |
