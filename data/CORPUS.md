# Corpus — Tuyển sinh đại học Việt Nam năm 2026

## Phạm vi

Corpus hỗ trợ hỏi đáp về quy chế, điều kiện dự tuyển, chính sách ưu tiên, số lượng
tuyển sinh, quy trình đăng ký, các mốc thời gian và thanh toán lệ phí trong mùa
tuyển sinh đại học năm 2026. Nguồn được giới hạn ở cơ quan nhà nước và cơ sở giáo
dục công lập để citation có thể kiểm chứng.

Ngày thu thập hiện tại được lưu riêng trong từng JSON; ngày ban hành và ngày đăng
được giữ trong metadata của từng tài liệu Markdown.

## Văn bản chính sách

1. **Thông tư 06/2026/TT-BGDĐT** — Quy chế tuyển sinh các ngành đào tạo trình độ
   đại học và ngành Giáo dục Mầm non trình độ cao đẳng. Bản PDF đã ký từ Công báo
   điện tử Chính phủ.
2. **Thông tư 34/2026/TT-BGDĐT** — Quy định việc xác định số lượng tuyển sinh.
   Bản PDF đã ký từ Công báo điện tử Chính phủ.
3. **Quyết định 955/QĐ-ĐHQGHN** — Quy chế tuyển sinh đại học tại Đại học Quốc
   gia Hà Nội. Bản PDF từ cổng thông tin chính thức của ĐHQGHN.

Chi tiết URL tải, landing page, kích thước và SHA-256 nằm trong
[`legal_sources.json`](legal_sources.json).

## Bài viết và hướng dẫn

Năm bài được thu thập từ chuyên trang Xây dựng chính sách, pháp luật của Cổng
Thông tin điện tử Chính phủ:

1. Hướng dẫn tuyển sinh đại học, cao đẳng năm 2026 theo Công văn 2304/BGDĐT-GDĐH.
2. Các mốc thời gian quan trọng của tuyển sinh đại học năm 2026.
3. Chính sách ưu tiên trong tuyển sinh đại học năm 2026.
4. Hướng dẫn thanh toán trực tuyến lệ phí xét tuyển năm 2026.
5. Những điểm mới trong Quy chế tuyển sinh đại học năm 2026.

Mỗi bản gốc JSON có `url`, `title`, `date_published`, `date_crawled`, `publisher`,
`topic` và `content_markdown`.

## Cấu trúc dữ liệu

```text
data/
├── landing/
│   ├── legal/          # 3 PDF gốc
│   └── news/           # 5 JSON gốc
├── standardized/
│   ├── legal/          # 3 Markdown có provenance/frontmatter
│   └── news/           # 5 Markdown có provenance/frontmatter
└── legal_sources.json  # manifest và checksum
```

Tái tạo corpus:

```bash
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news
python -m src.task3_convert_markdown
```

## Giới hạn sử dụng

- Corpus phản ánh nguồn được công bố cho mùa tuyển sinh 2026; không dùng để trả
  lời cho mùa tuyển sinh khác nếu chưa cập nhật nguồn.
- Quy định cấp quốc gia và quy định riêng của ĐHQGHN phải được phân biệt bằng
  `publisher`, `document_number` và citation; không khái quát quy định riêng của
  ĐHQGHN thành quy định áp dụng cho mọi trường.
- Khi các nguồn có khác biệt, văn bản quy phạm/pháp quy và văn bản ban hành sau
  được ưu tiên hơn bài giải thích báo chí.
