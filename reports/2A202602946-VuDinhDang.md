# Individual contribution report

## Thông tin

- Họ và tên: Vũ Đình Đăng
- Mã học viên: 2A202602946
- Nhóm: Vật lí 10–12 — Kết nối tri thức với cuộc sống
- Repository/branch: K4-L3A-RAG-Pipeline-Akatsuki

## Phần việc đã thực hiện

| Module/deliverable | Việc trực tiếp làm | File/bằng chứng | Trạng thái |
|---|---|---|---|
| Chunk/index | Chunk recursive 500/50, embedding BGE-M3, Chroma cosine | `src/task4_chunking_indexing.py` | Done |
| Hybrid retrieval | Dense, BM25L và RRF theo ID | `src/task5_semantic_search.py`, `src/task6_lexical_search.py`, `src/task7_reranking.py` | Done |
| Evaluation A/B | Chạy dense-only và hybrid + RRF với 4 metric | `src/evaluate_ragas.py`, `group_project/evaluation/evaluation_runs.json` | Done |

## Quyết định kỹ thuật

1. Dùng cùng `embed_texts()` cho index và query để tránh lệch embedding.
2. RRF chỉ hợp nhất thứ hạng, không cộng trực tiếp cosine với BM25.

## Kiểm thử và kết quả

- ChromaDB có 1.578 chunk.
- Contract tests cho chunk, dense, BM25 và RRF đạt.
- Evaluation ghi nhận hybrid + RRF đạt average 0.8406 so với dense-only 0.8365.

## Điều còn hạn chế

- BM25/RRF còn có thể đưa thêm chunk liên quan yếu với câu hỏi ngắn.

## Xác nhận đóng góp

- Ngày: 2026-09-20
- Tên thành viên: Vũ Đình Đăng
