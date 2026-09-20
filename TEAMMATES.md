# DANH SÁCH THÀNH VIÊN VÀ PHÂN CÔNG ĐỒ ÁN (TEAMMATES)

## Đồ án: Hệ thống RAG Pipeline — Trợ lý tra cứu IELTS Writing
* **Khóa học:** K4 AI Engineer / Advanced RAG
* **Nhóm:** L3A

---

## Bảng phân công nhiệm vụ và nhánh làm việc

| STT | Họ và tên | Mã học viên | Vai trò | Nhánh (Branch) | Phần việc chính phụ trách |
| :-: | :--- | :---: | :---: | :---: | :--- |
| 1 | **Nguyễn Vũ Anh** | **2A202602502** | Trưởng nhóm (Leader) / System Architect | `vuanh` | - Hoàn thiện PageIndex Vectorless Fallback: upload tự động, cache document ID (`pageindex_doc_ids.json`), timeout polling và parsing SearchResult (Task 8)<br>- Xây dựng Retrieval Pipeline và xử lý lỗi dịch vụ ngoại vi an toàn (Task 9)<br>- Generation có Citation & Safe Refusal (Task 10)<br>- Phát triển giao diện Chatbot tương tác Streamlit (`app.py`)<br>- Thiết kế kiến trúc tổng thể, cấu hình hệ thống (.env) và báo cáo nhóm |
| 2 | **Nguyễn Thành Duy** | **2A202602804** | Data Engineer | `duy` | - Thu thập 4 tài liệu PDF quy chế và tiêu chí chấm thi chính thức (Task 1)<br>- Crawl 12 bài viết hướng dẫn chuyên sâu từ IELTS Liz bằng Crawl4AI (Task 2)<br>- Chuẩn hóa toàn bộ dữ liệu sang định dạng Markdown qua MarkItDown (Task 3)<br>- Quản lý, tiền xử lý và kiểm thử nghiệm thu dữ liệu thô và chuẩn hóa trong `data/` |
| 3 | **Trương Việt Anh** | **2A202602444** | Vector DB & Semantic Search Specialist | `vietanh` | - Chiến lược phân đoạn văn bản đệ quy Recursive Character Splitter chunk 500, overlap 50 (Task 4)<br>- Tích hợp Gemini Embedding API (`gemini-embedding-001`, 3072 chiều) kiểm soát quota rate-limit (Task 4)<br>- Thiết lập ChromaDB persistent collection với cosine distance và xử lý metadata sạch (Task 4)<br>- Hiện thực hóa Dense Semantic Search (Task 5) |
| 4 | **Phạm Quang Đạt** | **2A202602704** | Search Algorithm & Evaluation Specialist | `quangdat` | - Thuật toán tìm kiếm từ khóa chính xác BM25Okapi với cơ chế tie-breaker (Task 6)<br>- Thuật toán Reranking Reciprocal Rank Fusion - RRF $k=60$ (Task 7)<br>- Xây dựng bộ Golden Dataset 15 ca Q&A tiếng Việt chuẩn xác cho bài thi IELTS Writing<br>- Thiết kế và thực hiện đánh giá thực nghiệm A/B Testing 4 chỉ số Ragas, hoàn thiện `RESULT.md` |

---

## Chi tiết liên kết Báo cáo đóng góp cá nhân (Individual Reports)

1. [Báo cáo cá nhân — Nguyễn Vũ Anh (2A202602502)](reports/2A202602502-NguyenVuAnh.md)
2. [Báo cáo cá nhân — Nguyễn Thành Duy (2A202602804)](reports/2A202602804-NguyenThanhDuy.md)
3. [Báo cáo cá nhân — Trương Việt Anh (2A202602444)](reports/2A202602444-TruongVietAnh.md)
4. [Báo cáo cá nhân — Phạm Quang Đạt (2A202602704)](reports/2A202602704-PhamQuangDat.md)

---

## Báo cáo tổng kết đồ án nhóm (Group Report)
* [Báo cáo tổng kết đồ án nhóm (GROUP_REPORT.md)](reports/GROUP_REPORT.md)
