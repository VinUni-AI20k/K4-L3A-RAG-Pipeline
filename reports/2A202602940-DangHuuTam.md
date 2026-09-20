# Báo cáo đóng góp cá nhân

## Thông tin

- Họ và tên: Đặng Hữu Tâm
- Mã học viên: 2A202602940
- Nhóm: BungChay
- Vai trò: Data
- Repository/branch: `K4-L3A-RAG-Pipeline-NguyenDoChienThang-2A202602442` / `data/vnulib-corpus-dang-huu-tam`, đã gộp vào `main` qua PR #2

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Thu thập tài liệu chính sách (Task 1) | Tải 3 PDF từ vnulib.edu.vn: Thông báo 106/TVTT, Thông báo 52/TB và hướng dẫn tra cứu mục lục trực tuyến. Tải bằng Chromium vì `requests`/`curl` báo lỗi SSL với site này. Ghi `sources.csv` (file, title, trang nguồn, URL PDF) để truy vết. | [src/task1_collect_legal_docs.py](../src/task1_collect_legal_docs.py), [data/landing/legal/](../data/landing/legal/); commit `c8b0742`, `64b4e73`, `ca59a48` | Done |
| Crawl bài viết (Task 2) | Crawl 7 trang vnulib bằng Crawl4AI (mượn trả, FAQs, tập huấn, cung cấp thông tin, thông báo điều chỉnh, nội quy, đăng ký thẻ). Chỉ lấy khung `.item-page` để bỏ menu, logo, sidebar. Mỗi bài một JSON đủ `url`, `title`, `date_crawled`, `content_markdown`. | [src/task2_crawl_news.py](../src/task2_crawl_news.py), [data/landing/news/](../data/landing/news/); commit `64b4e73`, `ca59a48` | Done |
| Chuẩn hoá Markdown (Task 3) | PDF có lớp chữ dùng MarkItDown; 2 PDF scan (Thông báo 106, 52) đọc bằng Gemini. Mỗi file `.md` có front matter (`doc_id`, `title`, `doc_type`, `source_url`, `source_file`). Chạy lại không sinh bản thừa. | [src/task3_convert_markdown.py](../src/task3_convert_markdown.py), [data/standardized/](../data/standardized/); commit `ca59a48` | Done |
| Đưa dữ liệu vào repo nhóm | Đưa corpus lên nhánh riêng và gộp vào `main`; kèm 5 file Markdown VNU có sẵn trong `data/thu-vien-vnulib/`. | PR #2 (merge commit `a3126fe`) | Done |

Tôi không nhận phần chunking/indexing, retrieval, generation/UI hoặc evaluation. Có dùng Claude Code hỗ trợ viết và chạy code (các commit có dòng `Co-Authored-By`).

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Tải PDF bằng Chromium thay vì `requests`, và không tắt kiểm tra SSL.
   **Lý do/evidence:** `curl` và `requests` báo `unable to get local issuer certificate` với vnulib.edu.vn (server thiếu chứng chỉ trung gian). Chromium tự bù chứng chỉ nên tải được bình thường.
   **Trade-off:** Chậm hơn và phải cài Chromium, nhưng không mất việc xác thực nguồn như khi dùng `verify=False`.

2. **Quyết định:** Đọc PDF scan bằng Gemini thay vì dùng thẳng kết quả MarkItDown, kèm đối chiếu chéo.
   **Lý do/evidence:** Với 2 PDF scan, MarkItDown ra chữ sai nặng (ví dụ "CỘNG HÒA XÃ HỘI" thành "ceNG HoA xA nor cnu"), sẽ làm retrieval sai. Bản Gemini của Thông báo 52 khớp với bảng tiền thế chân trên trang web; các mức phí chính của Thông báo 106 (45.000đ, 35.000đ, 95.000đ, 5.000đ/ngày) khớp với các trang web đã crawl.
   **Trade-off:** LLM có thể chép sai chữ; phải có API key và gửi văn bản công khai lên Google. Kết quả được giữ trong `standardized/` nên không gọi lại mỗi lần chạy.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: `pytest tests/test_acceptance.py -q`, đối chiếu thủ công Markdown với trang nguồn.
- Kết quả trước/sau: khi mới xong Task 1–2 (`standardized/` còn trống) là 2 passed, 3 failed; sau khi chạy Task 3, 3 test dữ liệu đều pass; trên `main` hiện tại là 5 passed (đã có golden dataset và `RESULT.md` của thành viên khác).
- Lỗi đã phát hiện và cách xử lý:
  - Lần crawl đầu lẫn logo, hotline, link bản đồ; sửa bằng `target_elements=[".item-page"]` (dùng `css_selector` thì mất `title`, ra "Unknown").
  - Hai PDF là cùng một văn bản (Thông báo 52); thay bằng một tài liệu khác.
  - Bài "Hướng dẫn sử dụng thư viện" chỉ là danh mục link; thay bằng trang FAQs.
  - Model `gemini-2.5-flash` bị Google từ chối; đọc PDF dùng biến `OCR_MODEL` (mặc định `gemini-3.6-flash`) và tự thử lại khi gặp lỗi 503.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: cụm rác "This email address is being protected from spambots..." còn lẫn trong một số bài; con số `180.000đ` trong Thông báo 106 chưa đối chiếu được với nguồn nào khác; tài liệu chính sách thứ 3 là hướng dẫn nghiệp vụ chứ không phải văn bản quy định (phần quy định như nội quy, đăng ký thẻ chỉ có dạng trang web); corpus còn nhỏ (10 nguồn).
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: lọc cụm rác về email trong Task 2, rồi đối chiếu thủ công Thông báo 106 với PDF gốc và các bài còn lại với trang nguồn.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Đặng Hữu Tâm
