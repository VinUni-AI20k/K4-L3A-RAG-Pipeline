"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Tầng landing giữ nguyên bản thô; tầng standardized là bản đã làm sạch để index.

Markdown crawl từ Wikipedia/Wikivoyage chỉ có 22–67% là văn xuôi, phần còn lại là
cú pháp link điều hướng, ảnh và mục chú thích. Giữ nguyên sẽ làm loãng embedding
và chiếm chỗ trong context, nên ở đây:
    - đổi [text](url) thành text, bỏ hẳn ![alt](url)
    - cắt các mục cuối trang (Tham khảo, Chú thích, Liên kết ngoài, References...)
    - gộp dòng trống thừa

Mỗi file giữ header title/source để tầng retrieval truy ngược được nguồn gốc.
"""

import json
import re
from pathlib import Path

from markitdown import MarkItDown


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

MIN_OUTPUT_CHARS = 200

# Heading báo hiệu phần còn lại chỉ là chú thích/điều hướng, không còn nội dung.
TAIL_SECTIONS = (
    "tham khảo", "chú thích", "liên kết ngoài", "xem thêm", "thư mục",
    "references", "external links", "see also", "further reading",
)


def clean_markdown(text: str) -> str:
    """Bỏ nhiễu điều hướng, giữ lại văn xuôi."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)        # ảnh
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)    # link -> anchor text
    text = re.sub(r"<[^>]+>", "", text)                      # tag HTML sót lại

    lines = text.splitlines()
    kept: list[str] = []
    for line in lines:
        # Chỉ cắt ở heading cấp 1-2. Wikivoyage dùng "### See also" làm tiểu mục
        # giữa bài, cắt ở đó sẽ mất luôn phần thị thực và đi lại.
        heading = re.match(r"^#{1,2}\s+(.*)$", line.strip())
        if heading and heading.group(1).strip().lower().rstrip(":") in TAIL_SECTIONS:
            break
        kept.append(line.rstrip())

    cleaned = "\n".join(kept)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def write_output(path: Path, body: str, label: str) -> bool:
    """Ghi file và từ chối output rỗng/quá ngắn."""
    if len(body.strip()) < MIN_OUTPUT_CHARS:
        print(f"Rejected: {label} — chỉ {len(body.strip())} ký tự sau chuẩn hóa")
        return False
    path.write_text(body, encoding="utf-8")
    print(f"Saved: {path.parent.name}/{path.name} ({len(body):,} ký tự)")
    return True


def convert_legal_docs() -> int:
    """Convert PDF/DOCX trong landing/legal sang standardized/legal."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkItDown()
    count = 0

    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue
        title = path.stem.replace("-", " ").capitalize()
        try:
            raw = converter.convert(str(path)).text_content
        except Exception as error:
            print(f"Failed: {path.name} — {type(error).__name__}: {error}")
            continue

        header = f"# {title}\n\n**Source:** {path.name}\n\n---\n\n"
        body = header + re.sub(r"\n{3,}", "\n\n", raw).strip()
        count += write_output(output_dir / f"{path.stem}.md", body, path.name)

    return count


def convert_news_articles() -> int:
    """Convert JSON trong landing/news sang standardized/news."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for path in sorted(news_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        header = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n---\n\n"
        )
        body = header + clean_markdown(data["content_markdown"])
        count += write_output(output_dir / f"{path.stem}.md", body, path.name)

    return count


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    legal = convert_legal_docs()
    news = convert_news_articles()
    print(f"\n{legal} legal + {news} news -> {OUTPUT_DIR}")
    if legal < 3 or news < 5:
        print("Cảnh báo: acceptance test cần >=3 legal và >=5 news.")


if __name__ == "__main__":
    convert_all()
