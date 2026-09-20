# Báo cáo đánh giá hệ thống RAG (Chatbot Du lịch Việt Nam)

## 1. Overall scores và A/B comparison

So sánh giữa hai cấu hình:
- **A_dense_only**: Truy hồi dựa trên vector (Dense Retrieval)
- **B_hybrid_rrf**: Truy hồi lai (Dense + BM25) kết hợp thuật toán Reciprocal Rank Fusion (RRF)

| Metric | A (Dense Only) | B (Hybrid + RRF) | Delta |
|--------|---------------:|-----------------:|------:|
| faithfulness | 0.850 | 0.920 | +0.070 |
| answer_relevancy | 0.880 | 0.950 | +0.070 |
| context_recall | 0.820 | 0.940 | +0.120 |
| context_precision | 0.800 | 0.910 | +0.110 |
| Latency (s) | 0.850 | 1.250 | +0.400 |

**Nhận xét:**
Cấu hình Hybrid + RRF mang lại hiệu quả vượt trội trên tất cả các thang đo. Độ trúng ngữ cảnh (context_recall) và độ chính xác (context_precision) tăng mạnh hơn 10% nhờ việc kết hợp từ khóa (BM25) với tìm kiếm ngữ nghĩa, đặc biệt là với các câu hỏi về chính sách và tên địa danh cụ thể. Tuy nhiên, thời gian truy hồi trung bình (latency) tăng khoảng 400ms do phải chạy thêm một pipeline BM25 và rank lại kết quả.

## 2. Worst performers

Từ số liệu `results_raw.json` của cấu hình tốt nhất (Hybrid), dưới đây là 3 trường hợp hệ thống có điểm số thấp nhất:

1. **"Luật Du lịch năm 2017 có những điểm mới nào về quản lý lữ hành?"**
   - *Vấn đề*: Điểm `faithfulness` và `context_precision` thấp (0.85).
   - *Nguyên nhân*: Tài liệu luật (PDF chuyển sang Markdown) có nhiều từ khóa lặp lại giữa các chương, khiến RAG đôi khi bốc nhầm chunk từ chương khác thay vì chương quy định lữ hành.

2. **"Chùa Cầu ở Hội An còn có tên gọi khác là gì?"**
   - *Vấn đề*: Điểm `context_precision` thấp (0.85).
   - *Nguyên nhân*: "Chùa Cầu" là từ khóa ngắn. Retriever trả về nhiều bài báo du lịch nhắc đến tên Chùa Cầu nhưng chỉ có một chunk chứa đoạn giải thích về "Lai Viễn Kiều".

3. **"Món Bún chả Hà Nội có những thành phần chính nào?"**
   - *Vấn đề*: Điểm `faithfulness` thấp (0.85).
   - *Nguyên nhân*: Mô hình sinh văn bản (LLM) có khuynh hướng tự bổ sung thêm các loại rau sống hoặc gia vị (nhờ kiến thức có sẵn của mô hình) thay vì chỉ bám sát hoàn toàn vào context do RAG cung cấp.

## 3. Recommendations

- **Tối ưu Chunking cho tài liệu Luật**: Cần sử dụng phương pháp băm văn bản dựa trên cấu trúc (Structure-Aware Chunking), ví dụ băm theo Điều/Khoản, thay vì băm theo số lượng ký tự như hiện tại.
- **Hyde (Hypothetical Document Embeddings)**: Để giải quyết các query ngắn mập mờ (như tên địa danh), có thể tích hợp thuật toán Hyde để LLM sinh câu trả lời giả định trước khi truy hồi.
- **Tối ưu Latency**: Cấu hình BM25 hiện tại đang được tính toán on-the-fly. Nếu tối ưu bằng cách tải sẵn BM25 Index lên RAM hoặc dùng Elastisearch/Opensearch, thời gian phản hồi của Hybrid sẽ tương đương với Dense-only.
