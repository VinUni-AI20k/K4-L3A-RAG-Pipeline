"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Luồng xử lý:
    landing/legal/*.pdf  --MarkItDown--> standardized/legal/*.md
    landing/news/*.json  --header+body--> standardized/news/*.md

Mỗi file Markdown mở đầu bằng metadata (title, source URL) nên từ bất kỳ file
standardized nào cũng truy ngược được về file landing và nguồn công khai.

Hai bước làm sạch cho văn bản Công báo:
    - Bỏ dòng header lặp lại ở mỗi trang ("CÔNG BÁO/Số ... /Ngày ...") vì nó
      chen vào giữa nội dung và gây nhiễu cho cả BM25 lẫn embedding.
    - Nối lại các dòng bị ngắt giữa câu do xuống dòng trong PDF, để splitter
      cắt chunk theo câu/đoạn thay vì theo dòng vật lý.

Tên file giữ nguyên theo file gốc nên chạy lại chỉ ghi đè, không sinh bản sao.
"""

import json
import re
import sys
from pathlib import Path

from markitdown import MarkItDown


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

LEGAL_SUFFIXES = {".pdf", ".doc", ".docx"}
MIN_OUTPUT_CHARS = 200

# Header lặp lại ở đầu/cuối mỗi trang Công báo, có thể kèm số trang hai bên.
CONGBAO_HEADER = re.compile(r"^\s*\d*\s*CÔNG BÁO/Số\s.*$", re.IGNORECASE)
# Dòng nối sang số Công báo tiếp theo, không thuộc nội dung văn bản.
CONGBAO_CONTINUED = re.compile(r"^\s*\(Xem tiếp Công báo số\s.*$", re.IGNORECASE)
# Dòng chỉ chứa số trang.
PAGE_NUMBER = re.compile(r"^\s*\d{1,3}\s*$")
# Dòng mở đầu một đơn vị cấu trúc mới (điều, khoản, điểm, chương...).
STRUCTURE_START = re.compile(
    r"^(?:\d+[\.\)]|[a-zđ]\)|Điều\s|Chương\s|Mục\s|Phần\s|Phụ lục)", re.IGNORECASE
)
SENTENCE_END = (".", ";", ":", "!", "?")


def remove_page_furniture(text: str) -> str:
    """Bỏ header Công báo, dòng nối số tiếp theo và dòng số trang."""
    noise = (CONGBAO_HEADER, CONGBAO_CONTINUED, PAGE_NUMBER)
    kept = [
        line
        for line in text.split("\n")
        if not any(pattern.match(line) for pattern in noise)
    ]
    return "\n".join(kept)


def reflow_paragraphs(text: str) -> str:
    """Nối các dòng bị PDF ngắt giữa câu thành đoạn hoàn chỉnh."""
    lines: list[str] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            lines.append("")
            continue

        previous = lines[-1] if lines else ""
        is_continuation = (
            previous
            and not previous.endswith(SENTENCE_END)
            and line[0].islower()
            and not STRUCTURE_START.match(line)
        )
        if is_continuation:
            lines[-1] = f"{previous} {line}"
        else:
            lines.append(line)

    joined = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", joined).strip()


def load_legal_manifest() -> dict[str, dict]:
    """Đọc manifest nguồn do Task 1 ghi ra, key theo tên file."""
    manifest_path = LANDING_DIR / "legal" / "sources.json"
    if not manifest_path.exists():
        return {}
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {entry["filename"]: entry for entry in entries}


def build_header(
    title: str,
    source: str,
    origin: str,
    doc_type: str,
    extra: dict[str, str] | None = None,
) -> str:
    """Khối metadata đặt ở đầu mỗi file Markdown, đóng lại bằng đường kẻ ngang."""
    lines = [
        f"# {title}",
        f"**Source:** {source}",
        f"**Origin:** {origin}",
        f"**Doc type:** {doc_type}",
    ]
    for label, value in (extra or {}).items():
        if value:
            lines.append(f"**{label}:** {value}")
    return "\n\n".join(lines) + "\n\n---\n\n"


def write_markdown(path: Path, content: str) -> bool:
    """Ghi file nếu nội dung đủ dài; trả về False khi bỏ qua."""
    if len(content.strip()) < MIN_OUTPUT_CHARS:
        print(f"  BỎ QUA: {path.name} chỉ có {len(content.strip())} ký tự")
        return False
    path.write_text(content, encoding="utf-8")
    print(f"  Saved: {path.name} ({len(content)} ký tự)")
    return True


def prune_stale(output_dir: Path, expected: set[str]) -> None:
    """Xoá Markdown không còn file nguồn tương ứng, tránh dữ liệu mồ côi."""
    for path in output_dir.glob("*.md"):
        if path.name not in expected:
            path.unlink()
            print(f"  Removed (không còn nguồn): {path.name}")


def convert_legal_docs() -> None:
    """Convert PDF/DOCX vào standardized/legal."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_legal_manifest()
    converter = MarkItDown()
    written: set[str] = set()

    print("Legal:")
    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() not in LEGAL_SUFFIXES:
            continue

        text = converter.convert(str(path)).text_content
        if not text.strip():
            print(f"  BỎ QUA: {path.name} không trích xuất được chữ (PDF scan?)")
            continue

        body = reflow_paragraphs(remove_page_furniture(text))
        entry = manifest.get(path.name, {})
        header = build_header(
            title=entry.get("title", path.stem),
            source=entry.get("url", "unknown"),
            origin=f"data/landing/legal/{path.name}",
            doc_type="legal",
        )
        output = output_dir / f"{path.stem}.md"
        if write_markdown(output, header + body):
            written.add(output.name)

    prune_stale(output_dir, written)


def convert_news_articles() -> None:
    """Convert JSON vào standardized/news."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    written: set[str] = set()

    print("News:")
    for path in sorted(news_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        body = data["content_markdown"].strip()

        header = build_header(
            title=data["title"],
            source=data["url"],
            origin=f"data/landing/news/{path.name}",
            doc_type="news",
            extra={
                "Crawled": data["date_crawled"],
                "Published": data.get("date_published", ""),
            },
        )

        output = output_dir / f"{path.stem}.md"
        if write_markdown(output, header + body):
            written.add(output.name)

    prune_stale(output_dir, written)


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    # Console Windows mặc định là cp1252 nên print tiếng Việt sẽ crash.
    if (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    convert_all()
