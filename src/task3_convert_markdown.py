"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cài đặt:
    Dependency MarkItDown đã được khai báo trong pyproject.toml.

-> Hoặc dùng công cụ nào bạn quen khác Markitdown
"""

import json
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

# Nội dung convert được ngắn hơn ngưỡng này (sau khi strip) sẽ bị coi là
# quá nghèo thông tin để đưa vào bước chunking/indexing tiếp theo -> không ghi file.
MIN_CONTENT_LENGTH = 200


def convert_legal_docs() -> None:
    """Convert PDF/DOC/DOCX trong data/landing/legal/ sang Markdown.

    Mỗi file nguồn convert lỗi không được làm hỏng cả batch: lỗi được bắt
    và báo riêng cho từng file, các file còn lại vẫn tiếp tục xử lý.
    """
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not legal_dir.is_dir():
        print(f"[legal] Cảnh báo: không tìm thấy thư mục {legal_dir}, bỏ qua.")
        return

    paths = sorted(
        path
        for path in legal_dir.iterdir()
        if path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in {".pdf", ".doc", ".docx"}
    )
    if not paths:
        print(f"[legal] Cảnh báo: thư mục {legal_dir} rỗng, không có gì để convert.")
        return

    converter = MarkItDown()
    converted = 0
    skipped = 0

    for path in paths:
        try:
            result = converter.convert(str(path))
            content = (result.text_content or "").strip()
        except Exception as exc:  # noqa: BLE001 - lỗi convert không được làm vỡ batch
            print(f"[legal] Lỗi convert '{path.name}': {exc}")
            skipped += 1
            continue

        if len(content) < MIN_CONTENT_LENGTH:
            print(
                f"[legal] Cảnh báo: '{path.name}' chỉ convert được "
                f"{len(content)} ký tự (< {MIN_CONTENT_LENGTH}), bỏ qua không ghi file."
            )
            skipped += 1
            continue

        # Thêm header đơn giản để giữ ngữ cảnh title/source, KHÔNG tính vào ngưỡng 200 ký tự.
        header = f"# {path.stem}\n\n"
        output_path = output_dir / f"{path.stem}.md"
        output_path.write_text(header + content, encoding="utf-8")
        print(f"[legal] Đã convert '{path.name}' -> '{output_path.name}' ({len(content)} ký tự).")
        converted += 1

    print(f"[legal] Hoàn tất: {converted} file đã convert, {skipped} file bị bỏ qua.")


def convert_news_articles() -> None:
    """Convert JSON trong data/landing/news/ sang Markdown.

    Thư mục news có thể rỗng (crawl bị hoãn) hoặc chưa tồn tại — hàm này
    KHÔNG được raise trong trường hợp đó, chỉ in cảnh báo rồi return.
    """
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not news_dir.is_dir():
        print(f"[news] Cảnh báo: không tìm thấy thư mục {news_dir}, bỏ qua.")
        return

    paths = sorted(news_dir.glob("*.json"))
    if not paths:
        print(
            f"[news] Cảnh báo: thư mục {news_dir} chưa có file JSON nào "
            "(crawl news có thể đang tạm hoãn), bỏ qua."
        )
        return

    required_fields = {"url", "title", "date_crawled", "content_markdown"}
    converted = 0
    skipped = 0

    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[news] Lỗi đọc/parse '{path.name}': {exc}")
            skipped += 1
            continue

        if not isinstance(data, dict) or not required_fields <= data.keys():
            missing = required_fields - (data.keys() if isinstance(data, dict) else set())
            print(f"[news] Cảnh báo: '{path.name}' thiếu field {missing or 'bắt buộc'}, bỏ qua.")
            skipped += 1
            continue

        content = str(data.get("content_markdown") or "").strip()
        if len(content) < MIN_CONTENT_LENGTH:
            print(
                f"[news] Cảnh báo: '{path.name}' chỉ có "
                f"{len(content)} ký tự nội dung (< {MIN_CONTENT_LENGTH}), bỏ qua không ghi file."
            )
            skipped += 1
            continue

        header = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n---\n\n"
        )
        output_path = output_dir / f"{path.stem}.md"
        output_path.write_text(header + content, encoding="utf-8")
        print(f"[news] Đã convert '{path.name}' -> '{output_path.name}' ({len(content)} ký tự).")
        converted += 1

    print(f"[news] Hoàn tất: {converted} file đã convert, {skipped} file bị bỏ qua.")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
