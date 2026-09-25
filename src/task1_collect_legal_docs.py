"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Đề tài: Chính sách người mua/người bán trên sàn TMĐT Shopee Việt Nam.

Nguồn: 5 trang chính sách công khai trên help.shopee.vn, được nhóm lưu lại dạng
Markdown (có frontmatter metadata) trong data/landing/legal/ và liệt kê trong
data/landing/legal/sources.csv.

Trang help.shopee.vn là trang HTML, không có bản PDF gốc. Để giữ đúng pipeline
landing (PDF/DOCX) → standardized (Markdown), bước này render mỗi tài liệu trong
sources.csv thành PDF (fpdf2 + font Unicode cho tiếng Việt). Task 3 sẽ convert
ngược PDF → Markdown bằng MarkItDown.

Chỉ tài liệu có trong sources.csv được đưa vào corpus; các file mẫu
(return-refund-policy.md, seller-warranty-policy.md trỏ tới example.com) bị bỏ qua.
"""

import csv
import re
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
SOURCES_CSV = DATA_DIR / "sources.csv"

FONT_CANDIDATES = [
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
]


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def load_sources() -> list[dict]:
    """Đọc sources.csv — danh sách tài liệu chính sách hợp lệ của nhóm."""
    with SOURCES_CSV.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Tách YAML frontmatter đơn giản (key: value) khỏi nội dung Markdown."""
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not match:
        return {}, text
    metadata = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            value = value.split("  #", 1)[0].strip().strip('"')
            metadata[key.strip()] = value
    return metadata, text[match.end():]


def find_font() -> Path:
    for path in FONT_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError(
        "No Unicode TTF font found for Vietnamese text; add one to FONT_CANDIDATES"
    )


def render_markdown_to_pdf(title: str, source_url: str, body: str, output: Path) -> None:
    """Render nội dung Markdown thành PDF, giữ tiêu đề và URL nguồn."""
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_title(title)
    pdf.set_subject(source_url)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("Body", fname=str(find_font()))
    pdf.add_page()

    pdf.set_font("Body", size=15)
    pdf.multi_cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Body", size=9)
    pdf.multi_cell(0, 5, f"Nguồn: {source_url}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Body", size=10)
    for line in body.splitlines():
        line = line.replace("\xa0", " ").rstrip()
        if not line.strip():
            pdf.ln(2)
            continue
        heading = re.match(r"^#{1,6}\s+(.*)", line)
        if heading:
            pdf.set_font("Body", size=12)
            pdf.multi_cell(0, 6, heading.group(1), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Body", size=10)
        else:
            pdf.multi_cell(0, 5, line.strip(), new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(output))


def download_documents() -> None:
    """Tạo PDF cho từng tài liệu trong sources.csv (idempotent)."""
    for row in load_sources():
        doc_id = row["doc_id"]
        markdown_path = DATA_DIR / f"{doc_id}.md"
        if not markdown_path.exists():
            print(f"Missing: {markdown_path.name} — skipped")
            continue
        _, body = split_frontmatter(markdown_path.read_text(encoding="utf-8"))
        output = DATA_DIR / f"{doc_id}.pdf"
        render_markdown_to_pdf(row["title"], row["source_url"], body, output)
        print(f"Saved: {output.name} ({output.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    setup_directory()
    download_documents()
