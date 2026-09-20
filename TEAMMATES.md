# Danh sách thành viên nhóm Phronesis — Day 08 RAG Pipeline

- **Lớp:** K4-L3A (VinUni AI20K Batch 04 · Lớp 3A)
- **Tên nhóm:** Phronesis
- **Đề tài:** Hệ thống Trợ lý Tra cứu Pháp lý & Tái cơ cấu Doanh nghiệp Nhà nước, Xử lý nợ xấu (Nghị định 357, 358, 359/2026/NĐ-CP, VAMC, DATC)
- **Repository:** https://github.com/nthanhwork/K4-L3A-RAG-Pipeline

---

## Phân công trách nhiệm & Đóng góp thành viên

| STT | Họ và tên | Mã học viên | Vai trò chính | Phạm vi công việc trực tiếp | Báo cáo cá nhân |
|:---:|:---|:---:|:---|:---|:---|
| 1 | **Nguyễn Thái Anh** | `2A202602810` | **Generation & UI Lead** | • Task 10: Xây dựng pipeline generation có citation chuẩn `[Document X]`, reordering chống *lost-in-the-middle*, safe refusal an toàn.<br>• Tích hợp Conversation Memory (+2đ Bonus) cho câu hỏi nối tiếp.<br>• Phát triển Streamlit UI (`app.py`) với Citation & Source Highlighting (+2đ Bonus), streaming output và bộ lọc nguồn. | [`reports/K4-L3A-2A202602810-NguyenThaiAnh.md`](reports/K4-L3A-2A202602810-NguyenThaiAnh.md) |
| 2 | **Ngọ Doãn Ngọc** | `2A202602635` | **Retrieval Lead** | • Task 7: Cài đặt thuật toán Reciprocal Rank Fusion (RRF, $k=60$) kết hợp Dense Vector và BM25.<br>• Task 8: Tích hợp PageIndex vectorless fallback có cơ chế cache document ID.<br>• Task 9: Xây dựng Retrieval Pipeline hoàn chỉnh và hiệu chuẩn thực nghiệm `SCORE_THRESHOLD = 0.45` (in-domain vs out-of-domain). | [`reports/K4-L3A-2A202602635-NgoDoanNgoc.md`](reports/K4-L3A-2A202602635-NgoDoanNgoc.md) |
| 3 | **Hoàng Ngọc Đăng Khoa** | `2A202602790` | **Evaluation Lead** | • Kiểm định nghiệm thu bộ Golden Dataset 16 grounded cases.<br>• Vận hành script đo lường tự động (`run_eval.py`), tính toán 4 metrics (Faithfulness, Relevance, Recall, Precision).<br>• Thực hiện A/B benchmark (Dense-only vs Hybrid RRF), phân tích chuyên sâu 3 ca kém nhất (Worst Performers) và xây dựng khuyến nghị cải tiến tại `RESULT.md`. | [`reports/K4-L3A-2A202602790-HoangNgocDangKhoa.md`](reports/K4-L3A-2A202602790-HoangNgocDangKhoa.md) |
| 4 | **Đoàn Quang Minh** | `2A202602711` | **Data Lead** | • Task 1: Thu thập 3 tài liệu pháp quy PDF gốc (NĐ 357, 358, 359/2026).<br>• Task 2: Thu thập 5 bài báo tài chính nghiệp vụ kèm đủ 4 trường metadata.<br>• Task 3: Chuẩn hóa dữ liệu sang Markdown theo cấu trúc `legal/` và `news/`.<br>• Task 4: Cài đặt chunking (500 chars / 50 overlap), embedding OpenAI và nạp 44 chunks vào ChromaDB. | [`reports/K4-L3A-2A202602711-DoanQuangMinh.md`](reports/K4-L3A-2A202602711-DoanQuangMinh.md) |

---

## Xác nhận nghiệm thu nhóm

Toàn bộ 4 thành viên nhóm Phronesis đã hoàn thành và tích hợp đầy đủ các phần việc được phân công, đạt 100% tiêu chí nghiệm thu kỹ thuật (**20/20 test passed** trên cả `tests/test_contracts.py` và `tests/test_acceptance.py`), sẵn sàng cho buổi demo và chấm điểm.
