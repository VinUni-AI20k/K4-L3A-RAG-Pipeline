"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Mỗi file output mang front matter YAML với source/title/doc_type/url để Task 4
dựng Document đúng contract mà không phải hard-code lại metadata.

Hai đường convert cho tài liệu legal:
    1. PDF band descriptors là bảng 4 cột không kẻ viền; MarkItDown trộn lẫn các
       cột thành văn bản vô nghĩa. Với các PDF này ta parse theo toạ độ bằng
       pdfplumber để tách đúng từng ô (band x tiêu chí).
    2. Các PDF còn lại là văn xuôi nên dùng MarkItDown.

Chạy:
    python -m src.task3_convert_markdown
"""

import json
import re
import warnings
from pathlib import Path

import pdfplumber
from markitdown import MarkItDown


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

MIN_OUTPUT_CHARS = 200

# Header/footer lặp lại trên mỗi trang PDF, không mang thông tin.
PDF_NOISE = re.compile(
    r"^\s*(page\s+\d+(\s+of\s+\d+)?|updated\s+\w+\s+\d{4}"
    r"|please visit ielts\.org for updates"
    r"|ielts is jointly owned by.*)\s*$",
    re.IGNORECASE,
)

# Rác điều hướng còn sót trong markdown crawl được.
WEB_NOISE = re.compile(
    r"^\s*(return to top of page|copyright\s*©.*|all rights reserved\.?"
    r"|privacy policy.*|log in|error: content is protected.*|skip to content"
    r"|share this.*|follow us.*|\*\s*)\s*$",
    re.IGNORECASE,
)

CRITERIA_ANCHORS = ("Task", "Coherence", "Lexical", "Grammatical")
HEADER_TOP, HEADER_BOTTOM = 78.0, 118.0
# Mặc định 3pt làm dính chữ ở trang Task 2 ("skilfullymanaged"); 1pt hết dính
# mà không vỡ từ (đo trên toàn bộ PDF).
WORD_X_TOLERANCE = 1.0


# --------------------------------------------------------------------------- #
# Tiện ích chung
# --------------------------------------------------------------------------- #

def front_matter(source: str, title: str, doc_type: str, url: str | None) -> str:
    """Metadata đặt đầu file, Task 4 đọc lại để dựng DocumentMetadata."""
    return (
        "---\n"
        f"source: {source}\n"
        f"title: {title}\n"
        f"doc_type: {doc_type}\n"
        f"url: {url or ''}\n"
        "---\n\n"
    )


def clean_lines(text: str, noise: re.Pattern) -> str:
    """Bỏ dòng rác, gộp dòng trống thừa và loại dòng lặp liên tiếp."""
    kept: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if noise.match(line):
            continue
        if line.strip() and kept and kept[-1].strip() == line.strip():
            continue  # header lặp giữa các trang
        kept.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def strip_web_markup(markdown: str) -> str:
    """Bỏ ảnh và giữ lại chữ của link; URL thô chỉ làm nhiễu embedding/BM25."""
    markdown = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown)
    # Dòng chỉ chứa đúng một link là mục điều hướng, không phải nội dung. Phải
    # lọc trước khi hạ link thành chữ, vì sau đó không còn dấu hiệu nhận biết.
    markdown = re.sub(
        r"^[ \t]*(?:[*+-][ \t]+)?\[[^\]]*\]\([^)]*\)[ \t]*$",
        "",
        markdown,
        flags=re.MULTILINE,
    )
    markdown = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", markdown)
    markdown = re.sub(r"<[^>]+>", "", markdown)
    return markdown


# --------------------------------------------------------------------------- #
# Legal: PDF bảng band descriptors
# --------------------------------------------------------------------------- #

def _column_bounds(page, words) -> list[float] | None:
    """Biên cột = đường kẻ dọc gần nhất bên trái mỗi tiêu đề tiêu chí."""
    anchors = {}
    for word in words:
        if word["text"] in CRITERIA_ANCHORS and HEADER_TOP <= word["top"] < HEADER_BOTTOM:
            anchors.setdefault(word["text"], word["x0"])
    if len(anchors) < 4:
        return None

    rules = sorted({round(e["x0"], 1) for e in page.edges if e["orientation"] == "v"})
    bounds = []
    for x in sorted(anchors.values()):
        left = [r for r in rules if r <= x]
        bounds.append(left[-1] if left else x - 6)
    return bounds + [page.width]


def _row_bounds(page) -> list[float]:
    """Biên hàng = các đường kẻ ngang của bảng, tính từ dưới dòng header."""
    rules = sorted({round(e["top"], 1) for e in page.edges if e["orientation"] == "h"})
    rows = [r for r in rules if r >= HEADER_BOTTOM - 1]
    merged: list[float] = []
    for r in rows:
        if not merged or r - merged[-1] > 2:
            merged.append(r)
    return merged


def _cell_text(words, x_start: float, x_end: float, top: float, bottom: float) -> str:
    cell = [
        w for w in words
        if x_start <= w["x0"] < x_end and top <= w["top"] < bottom
    ]
    # Gom theo dòng (làm tròn toạ độ dọc) rồi đọc trái sang phải.
    cell.sort(key=lambda w: (round(w["top"] / 3), w["x0"]))
    text = " ".join(w["text"] for w in cell)
    text = re.sub(r"\s+", " ", text).strip()
    # PDF hay dính chữ khi xuống dòng: "theappropriacy" -> "the appropriacy".
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    return re.sub(r"(?<=[–—])(?=[A-Za-z])", " ", text)


def _page_section(words) -> str:
    """Tên phần lấy từ tiêu đề đầu trang, ví dụ 'Writing Task 2'."""
    head = " ".join(w["text"] for w in words if w["top"] < HEADER_TOP - 30)
    match = re.search(r"Writing\s+Task\s+([12])", head)
    return f"Writing Task {match.group(1)}" if match else "Writing"


def extract_band_descriptor_markdown(path: Path) -> str | None:
    """Parse PDF band descriptors theo toạ độ. None nếu PDF không có bảng này."""
    sections: list[str] = []

    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=WORD_X_TOLERANCE)
            bounds = _column_bounds(page, words)
            if bounds is None:
                continue

            headers = [
                _cell_text(words, bounds[i], bounds[i + 1], HEADER_TOP, HEADER_BOTTOM)
                for i in range(4)
            ]
            rows = _row_bounds(page)
            section = _page_section(words)

            for top, bottom in zip(rows, rows[1:]):
                band = next(
                    (
                        w["text"] for w in words
                        if w["x0"] < bounds[0] and top <= w["top"] < bottom
                        and w["text"].isdigit() and len(w["text"]) == 1
                    ),
                    None,
                )
                if band is None:
                    continue  # hàng rỗng giữa các đường kẻ

                block = [f"## {section} — Band {band}\n"]
                for index, header in enumerate(headers):
                    body = _cell_text(words, bounds[index], bounds[index + 1], top, bottom)
                    if body:
                        block.append(f"### {header}\n\n{body}\n")
                sections.append("\n".join(block))

    return "\n".join(sections) if sections else None


def convert_legal_docs() -> None:
    """Convert PDF/DOCX vào standardized/legal."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = legal_dir / "sources.json"
    manifest = {}
    if manifest_path.exists():
        manifest = {
            entry["filename"]: entry
            for entry in json.loads(manifest_path.read_text(encoding="utf-8"))
        }

    converter = MarkItDown()
    count = 0

    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue

        meta = manifest.get(path.name, {})
        title = meta.get("title") or path.stem.replace("-", " ").title()
        url = meta.get("url")

        body = None
        if path.suffix.lower() == ".pdf":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                body = extract_band_descriptor_markdown(path)
            mode = "pdfplumber/table"

        if body is None:
            body = converter.convert(str(path)).text_content
            mode = "markitdown"

        body = clean_lines(body, PDF_NOISE)
        if len(body) < MIN_OUTPUT_CHARS:
            print(f"SKIP {path.name}: nội dung quá ngắn ({len(body)} ký tự)")
            continue

        output = output_dir / f"{path.stem}.md"
        output.write_text(
            front_matter(path.name, title, "legal", url) + f"# {title}\n\n{body}\n",
            encoding="utf-8",
        )
        count += 1
        print(f"OK   legal/{output.name} ({len(body):,} ký tự, {mode})")

    print(f"Legal: {count} file")


# --------------------------------------------------------------------------- #
# News: JSON đã crawl
# --------------------------------------------------------------------------- #

def convert_news_articles() -> None:
    """Convert JSON vào standardized/news."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for path in sorted(news_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))

        body = clean_lines(strip_web_markup(data["content_markdown"]), WEB_NOISE)
        if len(body) < MIN_OUTPUT_CHARS:
            print(f"SKIP {path.name}: nội dung quá ngắn ({len(body)} ký tự)")
            continue

        title = data["title"]
        header = (
            f"# {title}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n---\n\n"
        )
        output = output_dir / f"{path.stem}.md"
        output.write_text(
            front_matter(path.name, title, "news", data["url"]) + header + body + "\n",
            encoding="utf-8",
        )
        count += 1
        print(f"OK   news/{output.name} ({len(body):,} ký tự)")

    print(f"News: {count} file")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()