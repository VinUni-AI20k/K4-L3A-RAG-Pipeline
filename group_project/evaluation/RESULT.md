# RAG evaluation results

## Run information

| Field | Value |
| --- | --- |
| Evaluation date | Config A: 2026-09-20 · Config B: 2026-09-21 |
| Framework and version | RAGAS 0.4.3, Python 3.11.9, ChromaDB 1.5.9, sentence-transformers 6.1.0 |
| Evaluator model | `gemini-3.5-flash-lite` (LLM), `BAAI/bge-m3` (embeddings cho answer relevance) |
| Generator model | `gemini-3.5-flash-lite`, temperature 0.3, top_p 0.9 |
| Embedding model | `BAAI/bge-m3`, 1024 chiều, chạy local trên CPU |
| Corpus version/commit | `7f2164d` — 11 file legal + 5 file news → 4.937 chunk (size 500, overlap 50, cắt theo ranh giới `Điều`) |
| Golden dataset size | 17 case in-domain + 3 case out-of-domain |
| `top_k` | 5 |
| Fallback threshold and calibration | 0.60, quét toàn dải trên 17 câu in-domain và 3 câu out-of-domain |

Dữ liệu thô từng case: `evaluation_runs.json`. Chạy lại: `python -m src.run_evaluation`
(thêm `A` hoặc `B` để chạy một config).

> **Hai config đo ở hai ngày khác nhau** vì hạn mức Gemini free tier (mỗi config
> tốn ~85 request). Cùng model, cùng corpus, cùng golden dataset, cùng `top_k`.
> Tuy nhiên `gemini-3.5-flash-lite` **bỏ qua tham số `temperature`**, nên hai lần
> chạy cùng input vẫn có thể lệch nhẹ. **Delta nhỏ hơn ~0.03 không nên diễn giải
> là khác biệt thật.**

## Configurations

- **Config A — dense-only:** `retrieve(query, top_k=5, use_reranking=False)`. Chỉ
  semantic search trên ChromaDB (cosine), lấy top-5 trực tiếp từ dense.
- **Config B — hybrid + RRF:** `retrieve(query, top_k=5, use_reranking=True)`.
  Dense + BM25, hợp nhất bằng Reciprocal Rank Fusion `1/(60 + rank)`.

Hai config dùng chung golden dataset, generator, evaluator, `SYSTEM_PROMPT` của
Task 10 và `top_k`; khác duy nhất ở tham số `use_reranking`.

## Overall scores

17 case, không có ô NaN nào ở cả hai config.

| Metric | Config A | Config B | Delta B−A |
| --- | ---: | ---: | ---: |
| Faithfulness | 0.873 | 0.917 | **+0.044** |
| Answer relevance | 0.791 | 0.763 | −0.028 |
| Context recall | 0.765 | 0.765 | 0.000 |
| Context precision | 0.644 | 0.642 | −0.002 |
| **Average** | **0.768** | **0.772** | **+0.004** |

## A/B comparison

- **Cấu hình tốt hơn: Config B — hybrid + RRF, nhưng khác biệt rất nhỏ.**
- **Evidence:** chỉ `faithfulness` vượt ngưỡng nhiễu (+0.044) — câu trả lời của B
  bám bằng chứng chặt hơn. Ba chỉ số còn lại nằm trong khoảng nhiễu: answer
  relevance giảm 0.028, context recall **bằng nhau tuyệt đối** (0.765), context
  precision chênh 0.002. Trung bình chỉ hơn 0.004.
- **Kết luận thẳng thắn:** với corpus và bộ câu hỏi này, **RRF gần như không cải
  thiện chất lượng truy xuất**. `context_recall` giống hệt nhau là dấu hiệu rõ
  nhất: BM25 không kéo về được đoạn nào mà dense bỏ sót.
- **Trade-off về latency/cost:** hybrid thêm một lần BM25 (0,06 giây khi index đã
  cache) và một lần RRF, không tốn thêm request API. `retrieve()` đầy đủ mất 0,75
  giây, trong khi một lần gọi LLM mất 1,4 giây. Chi phí không đáng kể, nên vẫn
  nên giữ Config B vì faithfulness cao hơn — nhưng đừng kỳ vọng nó cứu được các
  câu đang thất bại.

### Giả thuyết đã bị bác bỏ

Trước khi đo, nhóm dự đoán hybrid sẽ sửa được các câu hỏi về mức phạt bằng số vì
BM25 khớp chuỗi chính xác. **Kết quả bác bỏ giả thuyết này:** cả ba câu thất bại
của Config A vẫn thất bại y hệt ở Config B, điểm gần như không đổi.

Nhóm cũng thử tự dựng một chỉ số retrieval (hit@5 dựa trên trùng chuỗi với
`expected_context`) để so A/B mà không tốn quota. Chỉ số này **đã bị loại bỏ** vì
không đáng tin trên corpus luật: nới lỏng thì cho 17/17 do các chunk trong cùng
một điều đều mang tiêu đề `Điều N` giống nhau nên khớp nhầm sang khoản sai; siết
chặt thì cho 6/17, mâu thuẫn với `context_recall = 0.765` của RAGAS. Báo cáo chỉ
dùng số RAGAS và kiểm chứng thủ công từng đoạn được truy xuất.

## Threshold calibration

| Nhóm | Số câu | Thấp nhất | Trung bình | Cao nhất |
| --- | ---: | ---: | ---: | ---: |
| In-domain | 17 | 0.541 | 0.713 | 0.794 |
| Out-of-domain | 3 | 0.365 | 0.457 | 0.589 |

Hai phân bố **chồng lấn**: câu in-domain yếu nhất (0.541 — "Thông tư 14/2025/TT-BXD
do cơ quan nào ban hành") thấp hơn câu out-of-domain mạnh nhất (0.589 — "Thủ tục
đăng ký kết hôn với người nước ngoài"). Không ngưỡng nào tách sạch, nên quét toàn
dải thay vì lấy điểm giữa:

| Ngưỡng | In-domain bị fallback nhầm | Out-of-domain bắt được |
| ---: | ---: | ---: |
| 0.50 | 0/17 | 2/3 |
| 0.55 | 1/17 | 2/3 |
| **0.59 – 0.62** | **1/17** | **3/3** |
| 0.63 | 2/17 | 3/3 |

Chọn **0.60**, giữa vùng tối ưu `[0.59, 0.62]`. Câu out-of-domain đạt 0.589 vì
corpus đầy ngôn ngữ thủ tục hành chính ("hồ sơ", "cơ quan có thẩm quyền", "trình
tự, thủ tục cấp mới") — embedding bắt được *văn phong hành chính* chứ chưa hẳn
bắt được *chủ đề giao thông*.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Mức phạt tiền cao nhất về nồng độ cồn đối với người lái xe ô tô là bao nhiêu? | A và B | 0.33 / 0.33 | 0.00 | 0.00 | 0.00 | retrieval | Không lấy được khoản 11 Điều 6 chứa mức 30–40 triệu. Từ "cao nhất" không xuất hiện trong văn bản luật nên không có tín hiệu để bám; BM25 cũng không giúp vì không có từ khoá chung. |
| 2 | Người lái xe ô tô chạy quá tốc độ trên 20 km/h đến 35 km/h bị phạt bao nhiêu tiền? | A và B | 0.50 / 0.50 | 0.00 | 0.00 | 0.00 | retrieval | Kiểm tra 5 đoạn Config B lấy về: **không đoạn nào chứa chuỗi "20 km/h đến 35 km/h"**, cũng không chứa mức 6.000.000 của Điều 6. Hai đoạn thuộc Điều 6 nhưng sai khoản, một đoạn thuộc Điều 7 (xe mô tô). |
| 3 | Lái xe ô tô có nồng độ cồn nhưng chưa vượt quá 50 miligam/100 mililít máu thì bị xử phạt thế nào? | A và B | 0.67 / 1.00 | 0.00 | 0.00 | 0.00 | retrieval | Lấy đúng điều nhưng sai khoản: retrieve được khoản nói mức trên 50 mg thay vì khoản "chưa vượt quá 50 mg". Hai khoản dùng gần như cùng bộ từ. |

Cả ba dừng ở **retrieval**, không phải generation. Khi thiếu bằng chứng, hệ thống
từ chối đúng như thiết kế thay vì bịa số — `answer_relevancy = 0.00` là vì câu
trả lời là lời từ chối, không phải vì trả lời sai. Đây là hành vi mong muốn, và
là lý do `faithfulness` vẫn ở mức 0.87–0.92 dù retrieval hỏng.

### Nguyên nhân gốc chung

Ba case đều thất bại ở cùng một chỗ: **không phân biệt được các khoản trong cùng
một điều luật**. Task 4 gắn tiêu đề `Điều N. ...` vào đầu mọi chunk để chunk
không mất ngữ cảnh — cách này đã sửa được lỗi trả nhầm mức phạt xe mô tô cho ô
tô. Nhưng nó tạo ra tác dụng phụ: mọi chunk trong cùng một điều giờ chia sẻ
150 ký tự đầu giống hệt nhau, khiến embedding của chúng xích lại gần nhau và
retrieval khó chọn đúng khoản. Điều 6 của Nghị định 168 có tới 11 khoản với cấu
trúc câu gần như giống nhau, chỉ khác con số.

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| ---: | --- | --- | --- | --- |
| 1 | Chuyển tiêu đề điều luật từ thân chunk sang metadata, chỉ ghép lại lúc `format_context` | Cả 3 case tệ nhất đều lấy sai khoản trong đúng điều; 89% chunk đang lặp cùng một tiêu đề làm loãng tín hiệu embedding | Tăng khả năng phân biệt khoản, kéo `context_recall` (0.765) và `context_precision` (0.644) lên | Chạy lại 3 case trên, kiểm tra đoạn top-5 có chứa đúng khoản không |
| 2 | Chunk theo **khoản** thay vì theo độ dài ký tự trong phạm vi điều | Điều 6 NĐ 168 có 11 khoản cấu trúc gần giống nhau; cắt theo 500 ký tự làm một khoản bị tách đôi hoặc dính hai khoản | Mỗi chunk là một đơn vị pháp lý trọn vẹn, giảm nhầm lẫn giữa các mức phạt | So `context_precision` trước/sau trên cùng 17 case |
| 3 | Bổ sung Nghị định 238/2026/NĐ-CP và 236/2026/NĐ-CP vào corpus | Tin bài trong corpus dẫn chiếu hai văn bản này 7 lượt nhưng bản thân chúng không có mặt | Loại bỏ nguy cơ trả lời theo quy định đã bị sửa đổi | Thêm câu hỏi về quy định hiệu lực 2026 vào golden dataset rồi đo lại |

Không khuyến nghị bỏ Config B: nó cho faithfulness cao hơn và gần như miễn phí về
chi phí. Nhưng ưu tiên cải thiện phải đặt vào **chunking**, không phải vào việc
tinh chỉnh thêm chiến lược hợp nhất thứ hạng.

## Bonus experiments

Chưa thực hiện. Quota API còn lại đã dùng hết cho việc hoàn tất bảng A/B chính.

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| --- | --- | ---: | ---: | --- |
| — | — | — | — | Chưa thực hiện |

## Ghi chú về độ tin cậy

- **Evaluator trùng generator** (`gemini-3.5-flash-lite` chấm chính nó) — thiên
  lệch self-evaluation đã biết. Nên đổi sang model khác họ khi có điều kiện.
- **`gemini-3.5-flash-lite` bỏ qua `temperature`** nên evaluator không chạy ở
  temperature 0; điểm dao động nhẹ giữa các lần chạy.
- **Hai config đo ở hai ngày** do hạn mức free tier. Delta dưới ~0.03 không phân
  biệt được với nhiễu giữa hai lần chạy.
- Lần chạy đầu có lỗi `400 INVALID_ARGUMENT` do `ResponseRelevancy` mặc định
  `strictness=3` dùng multiple candidates mà model này không hỗ trợ, và
  `TimeoutError` do timeout mặc định 180 giây. Đã đặt `strictness=1` và nâng
  timeout lên 600 giây; kết quả báo cáo ở trên không còn lỗi nào.
