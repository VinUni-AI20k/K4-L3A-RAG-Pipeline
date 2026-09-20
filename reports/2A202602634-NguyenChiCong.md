# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Chí Công
- Mã học viên: 2A202602634
- Nhóm: Vật lí 10–12 — Kết nối tri thức với cuộc sống
- Repository/branch: K4-L3A-RAG-Pipeline-Akatsuki

## Phần việc đã thực hiện

| Module/deliverable | Việc trực tiếp làm                                     | File/bằng chứng                      | Trạng thái    |
| ------------------ | ------------------------------------------------------ | ------------------------------------ | ------------- |
| Fallback           | Nối PageIndex tùy chọn, timeout, cache document ID     | `src/task8_pageindex_vectorless.py`  | Done/Optional |
| Retrieval pipeline | Dùng dense cosine threshold và hybrid fallback an toàn | `src/task9_retrieval_pipeline.py`    | Done          |
| Generation         | OpenAI `o4-mini`, citation và safe refusal             | `src/task10_generation.py`           | Done          |
| Evaluation report  | Tổng hợp metric, A/B comparison và recommendations     | `group_project/evaluation/RESULT.md` | Done          |

## Quyết định kỹ thuật

1. Không để lỗi PageIndex làm crash pipeline; khi lỗi giữ kết quả hybrid.
2. Reasoning model `o4-mini` không gửi `top_p`, vì API từ chối tham số này.

## Kiểm thử và kết quả

- Query thật trả lời có citation `[Document N]`.
- Contract và fallback tests đạt; PageIndex cloud chưa upload vì không có key.
- Báo cáo A/B dùng cùng 15 câu, prompt và generator cho hai cấu hình.

## Điều còn hạn chế

- Chưa triển khai dispatcher Gemini/Anthropic; nhóm chọn OpenAI `o4-mini`.

## Xác nhận đóng góp

- Ngày: 2026-09-20
- Tên thành viên: Nguyễn Chí Công
