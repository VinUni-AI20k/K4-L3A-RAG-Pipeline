# RAG Evaluation Results

## Run Information

| Field                              | Value                                                                |
| ---------------------------------- | -------------------------------------------------------------------- |
| Evaluation date                    | 2026-09-20                                                           |
| Framework and version              | RAGAS 0.4.3 / Python 3.13                                            |
| Evaluator model                    | Gemini 3.1 Flash                                                     |
| Generator model                    | Gemini 3.1 Flash                                                     |
| Embedding model                    | Gemini embedding-001                                                 |
| Corpus version/commit              | Local corpus Vịnh Hạ Long                                            |
| Golden dataset size                | 18                                                                   |
| `top_k`                            | 5                                                                    |
| Fallback threshold and calibration | Dense cosine 0.30, calibrated on in-domain and out-of-domain queries |

## Configurations

* **Config A – Dense-only:** Dense retrieval, không sử dụng BM25, không sử dụng RRF, `top_k=5`.
* **Config B – Hybrid + RRF:** Dense + BM25, RRF `k=60`, `top_k=5`.

Hai config sử dụng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay đổi retrieval strategy.

## Overall Scores

| Metric            | Config A |  Config B |  Delta B−A |
| ----------------- | -------: | --------: | ---------: |
| Faithfulness      |     0.84 |      0.88 |      +0.04 |
| Answer relevance  |     0.81 |      0.86 |      +0.05 |
| Context recall    |     0.76 |      0.84 |      +0.08 |
| Context precision |     0.79 |      0.85 |      +0.06 |
| **Average**       | **0.80** | **0.858** | **+0.058** |

## A/B Comparison

* **Cấu hình có kết quả cao hơn:** Config B – Hybrid + RRF.
* **Average score** tăng từ `0.80` lên `0.858`, tương ứng mức cải thiện `+0.058`.
* Cải thiện lớn nhất nằm ở **Context Recall**, tăng từ `0.76` lên `0.84`.
* **Context Precision** tăng từ `0.79` lên `0.85`, cho thấy phần lớn context bổ sung từ hybrid retrieval vẫn có liên quan đến câu hỏi.
* **Faithfulness** tăng từ `0.84` lên `0.88`, cho thấy câu trả lời có mức độ bám sát evidence được retrieval tốt hơn.
* **Answer Relevance** tăng từ `0.81` lên `0.86`.

### Evidence

BM25 hỗ trợ tốt các truy vấn chứa từ khóa chính xác như:

* Số hiệu văn bản.
* Tên địa danh.
* Tên cơ quan.
* Thuật ngữ pháp lý.
* Mốc thời gian.

Trong khi đó, dense retrieval sử dụng Gemini embedding giúp xử lý các truy vấn có cách diễn đạt khác với nội dung trong corpus nhưng có cùng ý nghĩa.

RRF kết hợp kết quả của hai retrieval strategy, nhờ đó giảm trường hợp một phương pháp retrieval đơn lẻ bỏ sót evidence.

### Trade-off về Latency/Cost

Hybrid retrieval phải thực hiện thêm BM25 và RRF nên latency cao hơn Dense-only.

Trong thử nghiệm trên corpus hiện tại, mức tăng latency tương đối nhỏ và không ảnh hưởng đáng kể đến trải nghiệm sử dụng.

Chi phí API gần như không thay đổi đáng kể vì BM25 và RRF được xử lý local, trong khi embedding và generation vẫn sử dụng cùng model.

## Worst Performers

|  # | Question                              | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause                                 |
| -: | ------------------------------------- | ------ | -----------: | --------: | -----: | --------: | ------------- | ------------------------------------------ |
|  1 | Số hiệu văn bản – query dạng viết tắt | A      |         0.68 |      0.65 |   0.51 |      0.54 | Retrieval     | Dense-only chưa bắt tốt exact match        |
|  2 | Hỏi ngày ban hành của văn bản pháp lý | B      |         0.77 |      0.75 |   0.64 |      0.68 | Retrieval     | Metadata nằm gần boundary giữa hai chunk   |
|  3 | Hỏi trải nghiệm du khách tổng hợp     | A      |         0.74 |      0.72 |   0.61 |      0.64 | Generation    | Evidence nằm phân tán trong nhiều bài news |

### Failure Analysis

**Worst case 1 – Exact-match query**

Dense retrieval hoạt động dựa trên semantic similarity nên đôi khi chưa ưu tiên đúng các chuỗi đặc biệt như số hiệu văn bản hoặc từ viết tắt.

BM25 xử lý trường hợp này tốt hơn vì có khả năng matching trực tiếp token xuất hiện trong query.

**Worst case 2 – Metadata boundary**

Một số metadata như ngày ban hành, cơ quan ban hành hoặc người ký nằm gần ranh giới chunk. Điều này có thể khiến retrieval lấy được nội dung chính nhưng thiếu metadata cần thiết để trả lời chính xác.

**Worst case 3 – Multi-document question**

Một số câu hỏi yêu cầu tổng hợp trải nghiệm du khách từ nhiều bài viết. Evidence bị phân tán giữa nhiều document nên generation cần tổng hợp nhiều context hơn so với câu hỏi factual thông thường.

## Recommendations

| Priority | Action                                                                    | Evidence from failure analysis | Expected impact                             | How to verify                                |
| -------: | ------------------------------------------------------------------------- | ------------------------------ | ------------------------------------------- | -------------------------------------------- |
|        1 | Giữ nguyên số hiệu và metadata pháp lý trong chunk, đồng thời tối ưu BM25 | Worst case 1                   | Tăng Context Recall cho exact-match query   | Chạy lại nhóm query chứa số hiệu/tên văn bản |
|        2 | Tăng chunk overlap quanh metadata                                         | Worst case 2                   | Giảm mất ngày ban hành, cơ quan và người ký | Kiểm tra chunk đầu/cuối của từng văn bản     |
|        3 | Làm sạch heading, menu và navigation trong news                           | Worst case 3                   | Tăng Context Precision và giảm nhiễu        | So sánh context trước/sau normalization      |
|        4 | Điều chỉnh `top_k` theo loại query                                        | Multi-document queries         | Tăng evidence cho câu hỏi tổng hợp          | A/B test `top_k=5` và `top_k=7`              |
|        5 | Bổ sung metadata filtering                                                | Legal queries                  | Thu hẹp phạm vi retrieval                   | So sánh retrieval có/không metadata filter   |

## Bonus Experiments

Ngoài hai cấu hình retrieval chính, nhóm thực hiện thêm thử nghiệm liên quan đến conversation memory và khả năng hiển thị nguồn.

| Experiment             | Baseline                       |                                         Metric delta | Latency/cost delta | Conclusion                                                        |
| ---------------------- | ------------------------------ | ---------------------------------------------------: | -----------------: | ----------------------------------------------------------------- |
| Conversation memory    | Không có memory                | Answer relevance **+0.05**, Context recall **+0.04** |  Latency **+4.8%** | Cải thiện rõ các câu hỏi follow-up và truy vấn phụ thuộc ngữ cảnh |
| UI source highlighting | Hiển thị nguồn dạng text thuần |                         Citation usability **+0.10** |  Latency **+0.7%** | Giúp kiểm tra evidence và nguồn citation thuận tiện hơn           |

