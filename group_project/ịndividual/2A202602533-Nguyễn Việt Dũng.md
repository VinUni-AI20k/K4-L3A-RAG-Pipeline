# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Việt Dũng
- Mã học viên: 2A202602533
- Nhóm: ScoutX - Track B — Hybrid Retrieval & Fallback Pipeline
- Repository/branch: `PhucBao1/K4-L3A-RAG-Pipeline` / branch `dung-02533`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 5 — Semantic Search | Query vector embeddings từ ChromaDB, chuyển cosine distance sang similarity (`1.0 - distance`), sort giảm dần theo score đúng chuẩn `SearchResult`. | `src/task5_semantic_search.py` | Done |
| Task 6 — Lexical Search | Xây dựng BM25 index bằng `BM25Okapi`, gán IDF positive floor tránh zero-division/log(1)=0 với small corpus, lọc score > 0. | `src/task6_lexical_search.py` | Done |
| Task 7 — RRF Reranking | Cài đặt thuật toán Reciprocal Rank Fusion: $RRF(d) = \sum 1/(60+rank)$, khử trùng lặp `id` và gộp ranking công bằng, đổi method sang `hybrid`. | `src/task7_reranking.py` | Done |
| Task 8 — Vectorless Fallback | Thiết kế interface PageIndex fallback, xử lý cache upload ID tài liệu và bọc exception graceful handling. | `src/task8_pageindex_vectorless.py` | Done |
| Task 9 — Retrieval Pipeline | Nhạc trưởng điều phối: query dense & lexical với pool `top_k * 2`, RRF 1 lần duy nhất, kích hoạt fallback theo cosine score gốc của dense và chống crash khi provider ngoài lỗi. | `src/task9_retrieval_pipeline.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Sử dụng điểm Cosine Similarity gốc của Dense retrieval (`best_dense_score`) làm điều kiện kích hoạt Fallback thay vì dùng điểm RRF.  
   **Lý do/evidence:** Thang điểm RRF là tổng nghịch đảo thứ hạng ($\sum 1/(k+rank)$) thường chỉ dao động ở mức rất nhỏ (~0.01 - 0.03) và không phản ánh độ tương đồng ngữ nghĩa tuyệt đối. Nếu so sánh threshold với RRF score sẽ dẫn đến tình trạng luôn kích hoạt fallback sai lệch.  
   **Trade-off:** Cần kiểm tra dense trước khi quyết định fallback, nhưng bảo đảm được tính chính xác và phân tách rạch ròi giữa query trong domain và ngoài domain.

2. **Quyết định:** Thêm positive floor cho IDF trong BM25 (`bm25.idf[word] = 1.0` nếu `idf <= 0`) và Graceful Degradation cho Fallback.  
   **Lý do/evidence:** Với tập dữ liệu test nhỏ ($N=2, n=1$), công thức chuẩn của BM25Okapi tính ra $\ln(1.5/1.5) = \ln(1) = 0$, khiến điểm BM25 của mọi chunk đều bằng 0 và dẫn tới lỗi rỗng kết quả (`IndexError`). Ngoài ra, PageIndex là API bên thứ 3 nên khi timeout/lỗi cần tự động fallback về `hybrid` thay vì crash app.  
   **Trade-off:** Điều chỉnh nhẹ giá trị IDF cho từ hiếm trên tập cực nhỏ, nhưng đổi lại hệ thống luôn ổn định và vượt qua mọi test case biên.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: 
  + Unit & Contract tests: `pytest tests/test_contracts.py -v` (toàn bộ 8/8 test liên quan đến Track B đạt **PASSED** 100%).
  + Empirical query calibration trên toàn bộ 1,716 chunks thực tế:
    * Query in-domain: *"Thủ tục đăng ký hộ kinh doanh"* $\rightarrow$ Dense Cosine Score đạt **0.7578** (Top 1: `nghi-dinh-168-2025-nd-cp-dang-ky-ho-kinh-doanh.md`).
    * Query out-of-domain: *"Cách nấu phở bò Hà Nội truyền thống"* $\rightarrow$ Dense Cosine Score giảm mạnh còn **0.3413**.
    * Kết luận: Hiệu chỉnh và thiết lập ngưỡng `SCORE_THRESHOLD = 0.45` trong `.env` giúp phân tách rạch ròi và kích hoạt Fallback chuẩn xác.
- Kết quả trước/sau nếu có: 
  + Ban đầu `test_lexical_search_returns_bm25_contract` bị lỗi `IndexError` do IDF = 0 trên 2 docs test. Sau khi tối ưu hóa floor IDF, 100% test Track B đạt **PASSED** (8/8 contract tests).
  + Đóng góp vào kết quả đánh giá end-to-end của nhóm (theo `RESULT.md`): Pipeline Hybrid + RRF giúp tăng điểm trung bình toàn hệ thống từ **0.729 lên 0.761** so với Dense-only, đặc biệt Context Recall tăng vọt từ **0.633 lên 0.767** (+13.3%), chứng minh giá trị của thuật toán RRF trong việc dung hợp từ khóa định danh văn bản pháp luật.
- Lỗi đã phát hiện và cách xử lý: 
  + Lỗi toán học $\ln(1)=0$ của BM25Okapi trên tập test nhỏ: xử lý bằng IDF positive floor.
  + Lỗi `ModuleNotFoundError` khi load dotenv sớm (wrap try-except an toàn).
  + Lỗi nghẽn mạng khi tải model 2.2GB local (chuyển sang OpenAI `text-embedding-3-small`).
  + Phối hợp Peer-Review với đồng đội (Phúc Bảo qua PR #3 `fix/task6-task8-runtime-bugs`): phát hiện và xử lý 2 lỗi runtime khi tích hợp thực tế gồm biến `CORPUS` BM25 cần tự động load ngoài test context và bổ sung `import json` còn thiếu ở Task 8 fallback.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Hiện tại pipeline mới chỉ fallback sang PageIndex hoặc trả kết quả hybrid an toàn; nếu mạng offline hoàn toàn khi có query ngoài domain thì cơ chế phụ thuộc vào safe refusal của generator.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Thử nghiệm thêm Cross-Encoder reranker (như BGE-Reranker-Large hoặc Cohere Rerank) để so sánh hiệu năng ranking với thuật toán RRF.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20-09-2026
- Tên thành viên: Nguyễn Việt Dũng
