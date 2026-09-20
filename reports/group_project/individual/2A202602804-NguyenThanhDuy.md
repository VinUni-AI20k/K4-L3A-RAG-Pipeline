# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Thành Duy
- Mã học viên: 2A202602804
- Nhóm: K4-L3A
- Repository/branch: K4-L3A-RAG-Pipeline / duy

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Thu thập tài liệu quy chế/chính sách (Task 1) | Nghiên cứu và tìm kiếm 4 tài liệu PDF chính sách và tiêu chí chấm thi IELTS Writing chính thức (Task 1 & Task 2 Band Descriptors, Examiner Feedback Criteria, Model Answers Assessment); hiện thực hàm `download_documents` sử dụng `requests` kèm User-Agent, timeout và xử lý lỗi HTTP, lưu an toàn vào `data/landing/legal/` | `src/task1_collect_legal_docs.py`, `data/landing/legal/` (commit `ed8fe15`, `2de5768`) | Done |
| Cào dữ liệu bài viết/hướng dẫn (Task 2) | Thiết lập danh sách 12 URL công khai từ các nguồn hướng dẫn học và luyện thi uy tín (IELTS Liz); hiện thực hàm cào dữ liệu bất đồng bộ `crawl_article` bằng `Crawl4AI` (`AsyncWebCrawler`), chuẩn hóa cấu trúc JSON (url, title, date_crawled, content_markdown) và lưu vào `data/landing/news/` từ `article_01.json` đến `article_12.json` | `src/task2_crawl_news.py`, `data/landing/news/` (commit `ed8fe15`, `2de5768`) | Done |
| Chuẩn hóa dữ liệu sang Markdown (Task 3) | Hiện thực `convert_legal_docs` dùng `MarkItDown` để trích xuất văn bản từ PDF sang Markdown; hiện thực `convert_news_articles` đọc JSON, đính kèm metadata header (`Title`, `Source`, `Crawled`) và xuất sang `data/standardized/`; xử lý lọc bỏ file ẩn (.gitkeep), đảm bảo tính idempotent và không sinh file rỗng | `src/task3_convert_markdown.py`, `data/standardized/` (commit `ed8fe15`, `2de5768`) | Done |
| Kiểm thử nghiệm thu dữ liệu (Acceptance Tests) | Chạy và xác thực toàn bộ các kiểm thử về tính toàn vẹn dữ liệu trong `tests/test_acceptance.py`, đảm bảo vượt yêu cầu tối thiểu (4/3 PDF legal, 12/5 JSON news, 16 file Markdown chuẩn hóa độ dài > 200 ký tự) | `tests/test_acceptance.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Thu thập mở rộng tập dữ liệu (4 tài liệu pháp lý/quy chế và 12 bài viết chuyên sâu) vượt mức yêu cầu tối thiểu (3 legal, 5 news) và đồng nhất hóa định dạng Markdown kèm Metadata Header.  
   **Lý do/evidence:** Bộ quy chế chấm thi IELTS (Task 1 & Task 2 Band Descriptors) chứa nhiều thuật ngữ cô đọng và bảng biểu tiêu chí đánh giá. Việc bổ sung thêm tài liệu nhận xét của giám khảo (Examiner Feedback) và bài mẫu phân tích (Model Answers Assessment) cùng 12 bài viết chi tiết giúp mở rộng không gian ngữ nghĩa, tăng tỷ lệ bao phủ ngữ cảnh (Context Recall) và cung cấp đầy đủ căn cứ thực tế để các module downstream (Chunking, Dense/BM25 Search, Generation có Citation) hoạt động chính xác.  
   **Trade-off:** Tăng khối lượng dữ liệu cần cào và chuyển đổi, cần tinh chỉnh hàm trích xuất để không bị nghẽn mạng hay lỗi định dạng, nhưng đổi lại giúp RAG pipeline có nguồn tri thức phong phú và câu trả lời chất lượng cao hơn.

2. **Quyết định:** Ứng dụng `MarkItDown` cho PDF và `Crawl4AI` bất đồng bộ kèm bộ lọc làm sạch tiêu đề và siêu dữ liệu trước khi lưu trữ.  
   **Lý do/evidence:** PDF các thang điểm IELTS chứa định dạng bảng biểu phức tạp. `MarkItDown` giúp chuyển đổi định dạng bảng sang bảng Markdown nguyên vẹn mà không làm đứt gãy cấu trúc đoạn văn bản. Đồng thời, `Crawl4AI` cho phép trích xuất nội dung web sang Markdown sạch trực tiếp, loại bỏ các thành phần rác như banner quảng cáo, menu điều hướng. Việc làm sạch tiêu đề (loại bỏ hậu tố " - IELTS Liz") giúp metadata gọn gàng, hỗ trợ hiển thị citation rõ ràng trên giao diện chatbot.  
   **Trade-off:** Cần cài đặt môi trường trình duyệt Chromium headless cho Playwright/Crawl4AI, nhưng tiết kiệm đáng kể thời gian tiền xử lý và loại bỏ nhiễu cho bước embedding vector.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: 
  - `pytest tests/test_acceptance.py -k "test_corpus or test_standardized"`
  - Kiểm tra thủ công tính hợp lệ của metadata và định dạng Markdown sau khi convert.
- Kết quả trước/sau nếu có:
  - Trước: Thư mục `data/` chỉ có các file giữ chỗ rỗng `.gitkeep`, các hàm trong `task1`, `task2`, `task3` đều ném lỗi `NotImplementedError`, chạy acceptance test thất bại toàn bộ.
  - Sau: Hoàn thiện 100% mã nguồn 3 task, thu thập thành công 4 file PDF (> 50KB mỗi file), 12 file JSON đầy đủ 4 trường metadata, chuyển đổi thành 16 file Markdown chuẩn hóa (> 200 ký tự mỗi file). Toàn bộ 3 test case dữ liệu trong `test_acceptance.py` đều vượt qua xuất sắc.
- Lỗi đã phát hiện và cách xử lý:
  - Một số file PDF từ máy chủ tài liệu có cơ chế chặn User-Agent mặc định của python-requests: đã bổ sung header `User-Agent` mô phỏng trình duyệt chuẩn.
  - Tiêu đề crawl từ web thường bị dính kèm tên trang web (ví dụ: `... - IELTS Liz`): đã bổ sung logic chuẩn hóa chuỗi `split(" - IELTS Liz")[0].strip()` để giữ lại tiêu đề bài học sạch sẽ.
  - Thư mục landing có chứa file ẩn `.gitkeep` dễ gây lỗi khi duyệt file: đã thêm điều kiện kiểm tra `not path.name.startswith(".")` trong các hàm convert.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Một số bảng biểu phức tạp trong file PDF thang điểm khi convert sang Markdown dạng text thuần có thể bị mất một phần cấu trúc lưới trực quan, phụ thuộc vào khả năng phân giải văn bản của bộ parser.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Bổ sung thêm module OCR chuyên sâu (hoặc bộ trích xuất bảng chuyên dụng như `pdfplumber`/`camelot`) để trích xuất bảng tiêu chí chấm thi dạng ma trận điểm (Grid Band Matrix) chuẩn xác hơn nữa.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Thành Duy
