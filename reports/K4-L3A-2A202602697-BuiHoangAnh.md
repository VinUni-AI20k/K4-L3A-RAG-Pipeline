# Individual Contribution Report

## Thông tin

* **Họ và tên:** Bùi Hoàng Anh
* **Mã học viên:** 2A202602697
* **Nhóm:** K4-L3A
* **Repository/branch:** https://github.com/hoanganhb680-arch/K4-L3A-RAG-Pipeline / `hoanganh`

## Phần việc đã thực hiện

| Module/Deliverable     | Việc tôi trực tiếp làm                                                                                                            | File/Commit/PR                      | Trạng thái |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | ---------- |
| PageIndex fallback     | Hoàn thiện Task 8: đọc `PAGEINDEX_API_KEY`, xử lý upload/query an toàn khi thiếu API key và trả `pageindex` theo contract         | `src/task8_pageindex_vectorless.py` | Done       |
| Retrieval pipeline     | Hoàn thiện Task 9: gọi dense + BM25, fuse bằng RRF đúng một lần, dùng dense cosine gốc cho fallback, không crash khi provider lỗi | `src/task9_retrieval_pipeline.py`   | Done       |
| Generation có citation | Hoàn thiện Task 10: retrieve → reorder context → format title/source → gọi Gemini và trả `GenerationResult` có citation           | `src/task10_generation.py`          | Done       |
| UI kết nối             | Kết nối app Streamlit với `generate_with_citation`, hiển thị câu trả lời và nguồn trích xuất                                      | `app.py`                            | Done       |

Chỉ kê khai công việc có thể đối chiếu bằng file, commit, pull request, test hoặc kết quả evaluation.

## Quyết định kỹ thuật quan trọng

### 1. Giữ `sources` được sắp xếp theo score giảm dần

**Quyết định:** Giữ `sources` trong `generate_with_citation` được sắp xếp theo score giảm dần, mặc dù context trước đó được reorder để giảm hiện tượng *lost-in-the-middle*.

**Lý do/Evidence:** Contract của `SearchResult` yêu cầu results được sắp xếp theo score giảm dần. Nếu trả `sources` theo thứ tự context sau khi reorder thì test contract báo lỗi ordering.

**Trade-off:** Thứ tự context mà LLM nhìn thấy khác với thứ tự nguồn được trả về, nhưng cách này đảm bảo tính hợp lệ của contract và dễ kiểm chứng bằng test.

### 2. PageIndex fallback khi chưa có API key

**Quyết định:** Khi chưa cấu hình `PAGEINDEX_API_KEY`, PageIndex trả về danh sách rỗng thay vì làm pipeline bị crash.

**Lý do/Evidence:** Pipeline cần có khả năng chạy trong nhiều môi trường, kể cả khi chưa cấu hình biến môi trường của provider bên ngoài.

**Trade-off:** Chưa có bằng chứng đánh giá chất lượng retrieval từ PageIndex provider thật, nhưng đảm bảo pipeline vẫn hoạt động ổn định khi thiếu cấu hình PageIndex.

## Kiểm thử và kết quả

* **Query đã dùng:** `Vịnh Hạ Long được UNESCO công nhận là gì?`
* **Retrieval source:** `hybrid`
* **Số lượng sources:** `3`
* **Generation:** Câu trả lời có citation `[Document 1]`.

**Lỗi đã phát hiện:**

```text
search results must be sorted by score descending
```

**Cách xử lý:** Tách riêng hai cấu trúc:

* `context_reordered`: dùng làm context đưa vào LLM nhằm giảm *lost-in-the-middle*.
* `sources_sorted`: giữ sources theo score giảm dần để đáp ứng contract của `SearchResult`.

## Điểm còn hạn chế

Một hạn chế cụ thể của phần tôi thực hiện là PageIndex hiện vẫn trả fallback rỗng khi chưa có `PAGEINDEX_API_KEY`.

Nếu có thêm thời gian, thay đổi ưu tiên tôi sẽ thực hiện là cấu hình PageIndex provider thật và tiến hành evaluation để đo mức cải thiện retrieval trong trường hợp corpus không có kết quả dense retrieval phù hợp.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phạm vi công việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

* **Ngày:** 2026-09-20
* **Tên thành viên:** Bùi Hoàng Anh
