# Báo cáo đóng góp cá nhân

## Thông tin

- Họ và tên: Đoàn Tuấn Long
- Mã học viên: 2A202602609
- Nhóm/lớp: K4-L3A
- Vai trò: Evaluation & Quality Assurance
- Nhánh: `DoanTuanLong-2A202602609`

## Phần việc/ownership

| Module/deliverable | Nội dung phụ trách | Artifact tích hợp | Trạng thái |
| --- | --- | --- | --- |
| Golden dataset | Duy trì 18 case dựa trên corpus thật, đủ ba trường bắt buộc | `group_project/evaluation/golden_dataset.json` | Done |
| A/B evaluation | Giữ cố định generator/prompt/top_k; chỉ đổi dense và hybrid + RRF | `run_evaluation.py`, `evaluation_details.json` | Done |
| Failure analysis | Tổng hợp bốn metric, delta, ba worst performers và root cause | `group_project/evaluation/RESULT.md` | Done |
| QA | Chạy contract, acceptance và full test | `tests/` | Done |

## Quyết định kỹ thuật

- Dùng cùng 18 câu, `top_k=5`, model và prompt cho cả hai cấu hình.
- Lưu từng case vào JSON để có thể resume và đối chiếu context ID.

## Kết quả

- Dense-only average: 0.8064.
- Hybrid + RRF average: 0.8282; delta +0.0219.
- Contract 15/15, acceptance 5/5 và full suite pass trên bản tích hợp.

## Hạn chế

- Bốn metric hiện là deterministic lexical proxies, có thể phạt paraphrase đúng.
- Mỗi cấu hình mới chạy một lần nên latency chưa đủ để kết luận chi phí.

## Xác nhận

Ownership trên được đối chiếu bằng artifact nhóm. Nhánh/commit cá nhân cần được giữ trên remote để giảng viên xác minh lịch sử đóng góp.

- Ngày: 20/09/2026
- Thành viên: Đoàn Tuấn Long