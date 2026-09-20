# RAG evaluation results

Báo cáo đo hai cấu hình trên cùng 15 câu: retrieval chạy offline, sau đó generation và evaluator LLM chạy live trên đúng top-5 context đã lưu của từng cấu hình. Bốn metric đã có số đo, nhưng context recall/precision là exact-span proxy và faithfulness/answer relevance là custom Gemini judge, không phải RAGAS. Không suy ra chất lượng tổng quát chỉ từ test pass hoặc một lần chấm.

## Run information

| Field | Value |
| --- | --- |
| Evaluation date | 2026-09-20; timestamp UTC trong `retrieval_results.json` và `generation_results.json` |
| Framework and version | NumPy 2.5.3, sentence-transformers 6.1.0, rank-bm25 0.2.2; exact-span evaluator và custom Gemini JSON judge |
| Evaluator model | Gemini `gemini-3.5-flash-lite`, temperature 0; chấm live 30/30 mẫu, 0 lỗi cuối cùng |
| Generator model | Gemini `gemini-3.5-flash-lite`, temperature 0.3, top-p 0.9; gọi live 30/30 câu trả lời |
| Embedding model | `BAAI/bge-m3`, sentence_transformers, 1024 chiều, cosine |
| Corpus version/commit | HEAD `056890f1c27d85df12e38fb5031267f5524038dd` + working tree; SHA-256 từng file trong `retrieval_results.json` |
| Golden dataset size | 15 câu: 6 legal + 9 news, phủ 3 legal + 5 news; mỗi câu có source và trích đoạn đã đối chiếu nguyên văn |
| Chunking | Recursive, 500 ký tự, overlap 50; 534 chunks |
| `top_k` | 5; lấy tối đa 10 candidates mỗi nhánh trước fusion |
| Fallback threshold and calibration | Tắt ở cả A/B để cô lập retrieval; ngưỡng mặc định ứng dụng 0.3 chưa được hiệu chỉnh bằng lần đo này |

Lệnh chạy lại từ repository root (PowerShell):

```powershell
.venv\Scripts\python.exe -m group_project.evaluation.evaluate_retrieval
.venv\Scripts\python.exe -m group_project.evaluation.evaluate_generation
.venv\Scripts\python.exe -m pytest -q
```

`evaluate_retrieval.py` yêu cầu embedding model local đã cache, chặn tải model qua mạng và không gọi API. Lần chạy gần nhất đã tái sử dụng 534 vector sau khi kiểm tra model, ID và nội dung chunk khớp corpus hiện tại. Chunk mới/thay đổi được embed trong bộ nhớ; script không upsert index. `retrieval_results.json` lưu hash corpus, hash golden dataset, cấu hình, score, nội dung và ID top-5 từng câu/cấu hình.

`evaluate_generation.py` kiểm tra hash của artifact retrieval, dùng lại đúng các context đã đo, gọi cùng generator/prompt cho A/B rồi chấm mỗi answer bằng cùng một rubric JSON. Script resume các mẫu đã thành công, giới hạn tốc độ để tuân thủ quota và loại provider error khỏi trung bình. `generation_results.json` lưu answer, metric, claim counts, rationale, latency, lỗi và hash liên kết với artifact retrieval. Sau lần đo này, toàn bộ test suite đạt `20 passed`.

## Configurations

- **Config A — dense-only:** cosine chính xác trên 534 vector, lấy top-5.
- **Config B — hybrid + RRF:** cùng dense top-10, BM25Plus top-10, dùng `task7_reranking.rerank_rrf` một lần với `k=60`, lấy top-5.

Hai config dùng cùng corpus, embedding, golden dataset, `top_k`, generator, system prompt và evaluator rubric; chỉ context retrieval khác nhau. PageIndex và fallback bị tắt để cô lập retrieval. Dense được tính bằng NumPy; kết quả không xác nhận thứ hạng HNSW gần đúng của Chroma hoặc luồng `retrieve()` có fallback trong ứng dụng.

## Overall scores

| Metric | Config A | Config B | Delta B−A |
| --- | ---: | ---: | ---: |
| Faithfulness — supported atomic claims | 0.9667 | 1.0000 | +0.0333 |
| Answer relevance — LLM rubric | 0.9333 | 0.9333 | 0.0000 |
| Context recall — exact gold-span proxy @5 | 0.8000 | 0.8667 | +0.0667 |
| Context precision — exact gold-span proxy @5 | 0.1600 | 0.1733 | +0.0133 |
| **Macro-average của 4 metric** | **0.7150** | **0.7433** | **+0.0283** |

Một chunk được gán relevant khi đúng `source` và chứa toàn bộ `expected_context`. Recall = số chunk relevant được lấy / tổng chunk relevant; precision = số chunk relevant được lấy / số chunk trả về; báo cáo lấy trung bình theo câu. Mỗi câu hiện có đúng một gold chunk, nên recall cũng là hit rate và precision tối đa là 0.2 khi trả 5 chunks. Đây là proxy dựa trên trích đoạn, không phải context recall/precision do RAGAS hoặc LLM chấm. Chunk diễn đạt tương đương ngoài trích đoạn đã gán nhãn có thể bị tính là miss.

Faithfulness = số atomic claim được context trực tiếp hỗ trợ / tổng atomic claim theo judge; answer relevance là điểm 0–1 cho mức độ trực tiếp, tập trung và đầy đủ đối với câu hỏi. Báo cáo lấy macro-average trên 15 câu, không có case lỗi. Generator và judge hiện dùng cùng model, judge chạy một lần ở temperature 0; vì vậy điểm có nguy cơ self-evaluation bias và chưa có độ đồng thuận giữa nhiều evaluator. Macro-average cuối bảng trộn hai metric LLM-judge với hai exact-span proxy, chỉ dùng để so sánh nội bộ A/B.

## A/B comparison

- Hybrid đạt exact-span hit 13/15, dense-only đạt 12/15. Hybrid tìm được `legal-03` tại `legal/25_2025_TT-BVHTTDL.md::chunk-12`, hạng 4; dense-only không có chunk này trong top-5. Không có câu giảm exact-span recall.
- Cả hai đạt 9/9 trên news; legal lần lượt đạt 3/6 và 4/6. Chưa đủ mẫu hoặc nhãn ngữ nghĩa để kết luận hybrid luôn tốt hơn hoặc trả lời chính xác hơn.
- Faithfulness tăng 0.0333 và answer relevance không đổi; macro-average bốn metric tăng 0.0283. Cải thiện answer rõ nhất là `legal-03`: A trả evidence khác ý hỏi và relevance 0.5, B lấy đúng gold chunk rồi đạt relevance 1.0.
- Latency trung bình của lần chạy gần nhất: A 235.53 ms, B 239.39 ms, tăng 3.86 ms. B tái sử dụng cùng lượt dense và cộng thời gian BM25/RRF, không phải hai lượt benchmark độc lập. Không tính tải model, chuẩn bị corpus/index hoặc generation. Lượt query đầu có cold-start lớn (A 1118.80 ms; B 1121.57 ms), trong khi median lần lượt là 173.55 ms và 178.00 ms; vì vậy số trung bình tuyệt đối chỉ mang tính tham khảo. Đây là một lượt đo, chưa warm-up inference, chưa có khoảng tin cậy hay benchmark concurrent.
- Generation latency trung bình là 1109.76 ms (A) và 1132.76 ms (B); judge latency trung bình là 1214.62 ms và 1059.20 ms. Các lượt retry do quota không được tính vào latency thành công. Retrieval offline không gọi API; generation/judge có gọi Gemini live nhưng artifact không cung cấp token usage nên chưa tính được chi phí tiền tệ.

## Worst performers

Ba câu có exact-span miss ở ít nhất một cấu hình. Recall/precision dưới đây là proxy đã định nghĩa; faithfulness/relevance lấy từ live judge.

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| ---: | --- | --- | --- | --- | ---: | ---: | --- | --- |
| 1 | `legal-01`: Thông tư 03/2026 quy định mức tối đa hay tối thiểu? | A và B | A 0.50; B 1.00 | A 0.50; B 0.00 | 0 | 0 | Retrieval | Gold chunk-7 vắng mặt nên cả hai answer từ chối. B hoàn toàn grounded nhưng không trả lời câu hỏi, do đó relevance bằng 0. |
| 2 | `legal-02`: Dịch vụ bảo tồn làng, bản hướng đến ai? | A và B | 1.00 | 1.00 | 0 | 0 | Nhãn đánh giá | Gold chunk-6 vắng mặt nhưng chunk-174 đứng đầu có evidence ngữ nghĩa đủ để hai cấu hình trả lời đúng. Exact-span proxy đánh giá thấp retrieval ở case này. |
| 3 | `legal-03`: Định mức tối đa theo Thông tư 25/2025 cần bảo đảm gì? | A | 1.00 | 0.50 | 0 | 0 | Retrieval | A trả một quy định có trong context nhưng khác ý hỏi. B đưa gold chunk vào hạng 4 và đạt faithfulness/relevance 1.00. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| ---: | --- | --- | --- | --- |
| 1 | Bổ sung nhãn relevant tương đương, giữ gold span làm nguồn đối chiếu | `legal-02` có evidence tại chunk-174 nhưng proxy báo miss | Tránh đánh giá thấp retrieval chỉ vì cách diễn đạt khác | Review thủ công top-5, chạy lại với nhãn mở rộng và báo riêng trước/sau |
| 2 | Thử chunk theo điều/mục, gắn tên và mã văn bản vào nội dung; hạn chế chunk tiêu đề đứng riêng | `legal-01` trả tiêu đề “Bảng định mức”; `legal-03` trả nhiều đoạn lặp | Lấy được điều khoản đầy đủ hơn | Re-index trong collection thử nghiệm, A/B cùng golden dataset và kiểm tra cả legal/news |
| 3 | Lặp lại bằng evaluator model độc lập hoặc RAGAS; thêm câu ngoài domain và hiệu chỉnh fallback | Judge hiện cùng model với generator, một lần chấm; dataset chỉ có câu trong domain | Giảm self-evaluation bias và kiểm chứng safe refusal | So sánh judge agreement, chạy nhiều seed/lần chấm; lưu riêng provider error và không tính lỗi API là answer thành công |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| --- | --- | --- | --- | --- |
| HyDE, query expansion, advanced reranker, conversation memory | Chưa chạy | Chưa đo | Chưa đo | Không có bằng chứng để nhận điểm bonus từ lần đo này |
