# Individual contribution report

Mỗi thành viên copy template này thành:

```text
reports/<student-id>-<short-name>.md
```

Giới hạn khuyến nghị: 1 trang, không chép lại README hoặc mô tả lý thuyết chung. Báo cáo không phải một bài pipeline cá nhân; mục đích là ghi nhận ownership và bằng chứng đóng góp trong sản phẩm nhóm.

---

## Thông tin

- Họ và tên: Bùi Tiến Cường
- Mã học viên:2A202602539
- Nhóm:Bochay
- Repository/branch:cuong

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 9 — retrieval pipeline | Kết nối semantic search và lexical search; hợp nhất kết quả bằng RRF khi bật reranking; dùng điểm dense gốc để kích hoạt PageIndex fallback; giữ kết quả hybrid nếu fallback không trả kết quả hoặc phát sinh lỗi. | [`src/task9_retrieval_pipeline.py`](../../src/task9_retrieval_pipeline.py); commit `2baaff8` (`Implement retrieval fallback and generation context`) | Done |
| Task 10 — generation and citation context | Hoàn thiện reorder chunks, format context kèm title/source, dispatch OpenAI/Gemini/Anthropic và safe refusal khi thiếu context hoặc provider lỗi. | [`src/task10_generation.py`](../../src/task10_generation.py); commit `2baaff8` | Done |

Chỉ kê khai công việc có thể đối chiếu bằng file, commit, pull request, test hoặc kết quả evaluation.

## Quyết định kỹ thuật quan trọng

Mô tả tối đa hai quyết định mà bạn trực tiếp tham gia:

1. **Quyết định:**  
   **Lý do/evidence:**  
   **Trade-off:**

2. **Quyết định:**  
   **Lý do/evidence:**  
   **Trade-off:**

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
- Kết quả trước/sau nếu có:
- Lỗi đã phát hiện và cách xử lý:

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm:
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện:

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày:
- Tên thành viên:
