# Individual contribution report

## Thông tin

- Họ và tên: Hoàng Trung Anh
- Mã học viên: 2A202602521
- Nhóm: Vật lí 10–12 — Kết nối tri thức với cuộc sống
- Repository/branch: K4-L3A-RAG-Pipeline-Akatsuki

## Phần việc đã thực hiện

| Module/deliverable | Việc trực tiếp làm | File/bằng chứng | Trạng thái |
|---|---|---|---|
| Thu thập/chuẩn hóa | Kiểm tra 3 PDF SGK, OCR tiếng Việt và metadata trang | `src/task3_convert_markdown.py`, `data/standardized/legal/` | Done |
| Nguồn công khai | Chuẩn hóa 5 bài viết kèm URL/license | `data/landing/SOURCES.md`, `data/standardized/news/` | Done |
| Golden dataset | Soạn 15 câu có expected answer/context và nguồn | `group_project/evaluation/golden_dataset.json` | Done |

## Quyết định kỹ thuật

1. Dùng Tesseract `vie` cho PDF scan vì lớp text PDF không đủ.
2. Giữ marker `PDF page` để truy nguồn và kiểm tra OCR.

## Kiểm thử và kết quả

- Ba PDF được chuyển thành Markdown; tổng corpus chuẩn hóa gồm 8 tài liệu.
- Kiểm tra acceptance cho nguồn và standardized output đạt.

## Điều còn hạn chế

- Một số công thức/bảng OCR cần kiểm tra thủ công thêm.

## Xác nhận đóng góp

- Ngày: 2026-09-20
- Tên thành viên: Hoàng Trung Anh
