# Individual contribution report

## Thông tin

- Họ và tên: Đinh Xuân Quyền
- Mã học viên: 2A202602358
- Nhóm: K4-L3A
- Repository/branch: main (tài khoản github: dinhxuanquyen)

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
| --- | --- | --- | --- |
| Task 4: Chunking & Indexing | Code hàm cắt văn bản thành các chunk nhỏ và lưu vào ChromaDB. | `src/task4_chunking_indexing.py` | Done |
| Task 5: Dense Search | Viết hàm tìm kiếm theo vector similarity. | `src/task5_dense_search.py` | Done |
| Task 6: Lexical Search | Triển khai tìm kiếm từ khóa dùng rank_bm25. | `src/task6_lexical_search.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng RecursiveCharacterTextSplitter để chia chunk với size 500, overlap 50.
   **Lý do/evidence:** Thử test vài cách thì thấy chia theo đoạn văn (paragraph) kiểu này giúp ý nghĩa không bị đứt đoạn quá nhiều.
   **Trade-off:** Một số đoạn ngắn bị dư ra, bù lại search chính xác hơn chút.
   
2. **Quyết định:** Chọn dùng HashingVectorizer cho embedding lúc test local thay vì tải model nặng.
   **Lý do/evidence:** Máy tính yếu tải model bge-m3 lâu quá, dùng hashing chạy cho nhanh để test pass được pipeline.
   **Trade-off:** Điểm semantic search không chuẩn lắm, nhưng đủ để check lỗi logic.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: Chạy `pytest tests/test_contracts.py`
- Kết quả trước/sau nếu có: Pass hết mấy hàm của task 4, 5, 6 sau mấy lần báo lỗi thiếu thư viện.
- Lỗi đã phát hiện và cách xử lý: Khúc BM25 hay bị lỗi index out of range do đếm sai số thứ tự chunk, em phải in ra check rồi sửa lại ID cho khớp với metadata.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Hàm search BM25 mỗi lần search lại phải load lại corpus build lại index nên hơi chậm.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Lưu cái file index BM25 ra đĩa (cache lại) để lần sau chạy đỡ mất công tính lại từ đầu.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Đinh Xuân Quyền
