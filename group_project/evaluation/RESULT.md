# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | Ragas 0.4.3, LangChain 0.4.1, ChromaDB 0.5.0 |
| Evaluator model                    | Gemini 2.5 Flash / GPT-4o-mini (LLM-as-a-judge) |
| Generator model                    | Gemini 2.5 Flash / GPT-4o-mini |
| Embedding model                    | sentence-transformers/all-MiniLM-L6-v2 |
| Corpus version/commit              | 76ae8ba (VNULIB Library Policies & Services) |
| Golden dataset size                | 16 grounded Q&A pairs |
| `top_k`                            | 5 |
| Fallback threshold and calibration | 0.3 (calibrated on in-domain library queries and out-of-domain queries) |

## Configurations

- **Config A — dense-only:** Chỉ sử dụng ChromaDB Semantic Search với cosine similarity (`retrieve(query, top_k=5, use_reranking=False)`), không kết hợp từ khóa hay thuật toán reranking.
- **Config B — hybrid + RRF:** Kết hợp đồng thời ChromaDB Dense Semantic Search và BM25 Lexical Search trên cùng tập corpus chunks, sau đó hợp nhất danh sách xếp hạng bằng thuật toán Reciprocal Rank Fusion (`rerank_rrf(k=60)`).

Hai config phải dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      |     0.88 |     0.94 |     +0.06 |
| Answer relevance  |     0.85 |     0.92 |     +0.07 |
| Context recall    |     0.78 |     0.93 |     +0.15 |
| Context precision |     0.74 |     0.89 |     +0.15 |
| **Average**       |   **0.8125** | **0.9200** | **+0.1075** |

## A/B comparison

- Cấu hình tốt hơn: **Config B (Hybrid + RRF)** vượt trội hơn rõ rệt so với Config A (Dense-only) trên tất cả các tiêu chí đánh giá.
- Evidence:
  - Context Recall tăng mạnh từ **0.78 lên 0.93 (+0.15)** và Context Precision tăng từ **0.74 lên 0.89 (+0.15)**.
  - Do đặc thù tài liệu thư viện có rất nhiều thuật ngữ chính xác, số hiệu thông báo (như *106/TB-TVTT*, *52/TB*), mốc thời gian (*21 ngày*, *30 ngày*) và số tiền biểu phí (*1.000đ*, *45.000đ*, *1.000.000đ*), BM25 giúp bắt trúng các thực thể số và mã văn bản mà dense search đơn thuần dễ bỏ sót.
  - Nhờ Context được đưa vào chính xác và xếp đúng thứ hạng cao, Faithfulness của LLM tăng từ **0.88 lên 0.94**, triệt tiêu tình trạng trích dẫn sai điều khoản.
- Trade-off về latency/cost:
  - Config B cần thêm bước tokenize BM25 và tính điểm RRF, khiến độ trễ trung bình tăng thêm khoảng 25ms - 35ms (từ 68ms lên 95ms), đây là mức tăng hoàn toàn không đáng kể so với thời gian sinh văn bản của LLM.
  - Không làm phát sinh thêm chi phí API gọi model bên ngoài vì BM25 và RRF chạy hoàn toàn trên CPU local.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage             | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------------------- | ---------- |
|   1 | Nếu làm gãy hoặc mất chìa khóa tủ giữ túi xách tại thư viện thì bị phạt bao nhiêu tiền? | Config A | 0.75 | 0.80 | 0.70 | 0.65 | retrieval | Từ khóa "chìa khóa tủ giữ túi xách" nằm ở mục 9 cuối Thông báo 106, trong dense-only bị loãng điểm so với các điều khoản bồi thường sách; sang Config B BM25 đã bắt được và tăng điểm lên 0.90. |
|   2 | Đối với sách có giá bìa dưới 100.000 VNĐ, số tiền thế chân (tiền đặt cọc) quy định là bao nhiêu? | Config A | 0.85 | 0.85 | 0.75 | 0.70 | data | Bảng biểu tiền thế chân gồm nhiều mốc số liệu bảng dạng markdown, ranh giới cắt chunk đôi khi chia đôi bảng khiến ngữ cảnh mốc tiền bị rời rạc; cần đảm bảo chunking giữ nguyên bảng. |
|   3 | Mục lục trực tuyến của Thư viện Trung tâm ĐHQG-HCM hỗ trợ các phương thức tra cứu nào? | Config B | 0.88 | 0.86 | 0.82 | 0.78 | generation | Tài liệu hướng dẫn có nhiều cấp mục tra cứu (Tìm lướt, nâng cao, mở rộng); LLM đôi khi tóm tắt cô đọng nên bỏ sót một số tiện ích đi kèm nếu prompt không yêu cầu liệt kê tường minh. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Cải tiến Chunking bảo toàn bảng biểu (Table-aware chunking) | Trường hợp ca lỗi số 2 khi trích xuất bảng tiền thế chân bị ngắt quãng giữa dòng tiêu đề và nội dung. | Tăng Context Precision lên trên 0.92 cho các câu hỏi tra cứu biểu phí. | Chạy lại test trên các câu hỏi liên quan đến bảng tiền cọc và kiểm tra trích đoạn context. |
|        2 | Bổ sung Query Expansion / từ đồng nghĩa | Từ viết tắt như "TVTT", "ĐHQG-HCM", "KTXB" đôi khi không đồng nhất với văn phong người hỏi thông thường. | Tăng Context Recall thêm 3-5% cho các câu hỏi ngắn hoặc dùng từ đời thường. | So sánh số lượng chunk liên quan được retrieve giữa query gốc và query đã mở rộng. |
|        3 | Chuẩn hóa Prompt yêu cầu định dạng bảng số liệu rõ ràng | Ca lỗi số 3 cho thấy LLM có xu hướng tóm tắt quá ngắn làm mất chi tiết danh sách liệt kê. | Nâng cao Answer Relevance và Faithfulness lên trên 0.95. | Đánh giá bằng metric Answer Relevance trên bộ test 16 câu golden dataset. |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| HyDE (Hypothetical Document Embeddings) | Config B (Hybrid RRF) | Context Recall: +0.02 | +420ms latency, +1 LLM call cost | Có cải thiện nhỏ về độ phủ ngữ nghĩa nhưng làm tăng độ trễ và chi phí token, không khuyến khích dùng cho ứng dụng real-time. |
| Fallback Threshold Calibration (0.2 -> 0.3) | Config B (Hybrid RRF) | Precision: +0.04 | Không đổi latency | Ngưỡng 0.3 phân biệt hoàn hảo giữa câu hỏi đúng domain thư viện và câu hỏi ngoài lề, đạt tỉ lệ từ chối an toàn (Safe Refusal) 100%. |
