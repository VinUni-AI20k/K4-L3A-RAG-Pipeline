# Individual contribution report

## Thông tin

- Họ và tên: Chung Văn Duy
- Mã học viên: 2A202602854
- Nhóm: Nhóm 2 (K4-L3A)
- Repository/branch: ratrichero/K4-L3A-RAG-Pipeline (branch: ChungVanDuy)

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Thu thập tin tức & mở bán Vinhomes | Crawl 5 bài báo tin tức/mở bán và bảng giá Vinhomes Ocean Park (1, 2, 3), làm sạch dữ liệu | PR #2, commit `f560447`, `data/landing/news/*.json` | Done |
| Chuẩn hóa dữ liệu Markdown (Task 3) | Xây dựng pipeline chuẩn hóa tài liệu legal và news sang Markdown chuẩn có header metadata (`Title`, `Source`, `Doc Type`, `Date`), loại bỏ trùng lặp và hỗ trợ đa định dạng (`.json`, `.md`, `.pdf`, `.docx`) | `src/task3_convert_markdown.py`, `data/standardized/` | Done |
| Chunking & Metadata Preservation (Task 4) | Hiện thực `load_documents()` và `chunk_documents()` sử dụng `RecursiveCharacterTextSplitter` (size 500, overlap 50), bảo toàn metadata nguồn và gán `chunk_index`, định danh ID ổn định | `src/task4_chunking_indexing.py` | Done |
| Vectorstore Indexing (Task 4) | Hiện thực `get_collection()` và `index_to_vectorstore()` upsert vào ChromaDB với metric cosine distance (`hnsw:space: cosine`), xử lý batch upsert an toàn | `src/task4_chunking_indexing.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định: Hỗ trợ nạp dữ liệu đa định dạng song song và lọc trùng lặp theo file stem trong Task 3**  
   **Lý do/evidence:** Thư mục `landing/news` và `landing/legal` có thể chứa đồng thời cả file cấu trúc `.json`/`.docx`/`.pdf` (cho test acceptance) lẫn `.md` (bản crawl nội dung). Bằng cách nhóm theo `stem` và ưu tiên nguồn có metadata giàu hơn, pipeline đảm bảo sinh đúng 8 tài liệu chuẩn hóa độc nhất, không tạo file rỗng hay nhân bản khi chạy lại.  
   **Trade-off:** Logic xử lý parser phức tạp hơn một chút so với việc chỉ đọc một định dạng cố định, nhưng đổi lại tính bền vững (robustness) và khả năng tương thích cao.

2. **Quyết định: Chọn strategy RecursiveCharacterTextSplitter với chunk_size=500, chunk_overlap=50 và batch upsert 100 vào ChromaDB**  
   **Lý do/evidence:** Văn bản chính sách và tin tức bất động sản có cấu trúc điều khoản, mục lục và bảng biểu phân cấp rõ ràng. Chunk size 500 ký tự giúp mỗi chunk chứa trọn vẹn một điều khoản hoặc chính sách ưu đãi cụ thể mà không bị cắt vụn, dung sai chiều dài luôn $\le 550$ ký tự thỏa mãn contract test `test_chunk_documents_preserves_identity_and_metadata`. Batch upsert 100 giúp hạn chế lỗi quá tải bộ nhớ và giới hạn request của vector database.  
   **Trade-off:** Kích thước chunk 500 có thể làm một số bảng biểu dài bị ngắt đôi, nhưng được bù đắp bằng overlap 50 ký tự để duy trì mạch thông tin liên kết.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - `pytest tests/test_acceptance.py -k "corpus or standardized" -v`
  - `pytest tests/test_contracts.py -k "signatures or validator or chunk_documents" -v`
  - `python -m src.task3_convert_markdown`
  - `python -m src.task4_chunking_indexing`
- Kết quả trước/sau:
  - Trước: Task 3 và Task 4 raise `NotImplementedError`, cả 3 bài test acceptance dữ liệu (`test_corpus_has_required_legal_documents`, `test_corpus_has_required_news_with_metadata`, `test_standardized_output_covers_both_source_types`) và contract test chunking đều bị FAILED.
  - Sau: 100% các bài test dữ liệu và contract test của Task 4 đều PASSED (8 passed, 7 deselected trong test contracts; 3/3 passed trong data acceptance tests).
- Lỗi đã phát hiện và cách xử lý:
  - Thư mục `landing/news` ban đầu chỉ có `.md`, khiến `test_corpus_has_required_news_with_metadata` fail vì thiếu `.json`. Đã tạo song song các file `.json` đầy đủ metadata `url`, `title`, `date_crawled`, `content_markdown`.
  - ChromaDB metadata không chấp nhận giá trị `None` ở một số client mode: Đã chuẩn hóa `url: None` thành chuỗi rỗng `""` trước khi upsert vào collection.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Tốc độ tải và encode embedding cục bộ với mô hình nặng như `BAAI/bge-m3` phụ thuộc nhiều vào tài nguyên máy tính nếu không sử dụng API cloud.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Tích hợp cơ chế Semantic Chunking hoặc MarkdownHeaderTextSplitter để chia chunk chính xác theo các Heading cấp 2, 3 của văn bản chính sách trước khi chia nhỏ theo Recursive Splitter.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Chung Văn Duy
