"""
Task 1 — Thu thập tài liệu chính sách/quy định (chủ đề: Du lịch).

1. Chọn tối thiểu 3 văn bản pháp luật du lịch từ nguồn công khai.
2. Nếu URL là file PDF/DOCX thì tải bytes; nếu là trang HTML thì trích toàn
   văn và tạo file .docx cục bộ từ nội dung đó.
3. Lưu file gốc vào data/landing/legal/, tên không dấu.

Ví dụ tài liệu nhóm chọn: Luật Du lịch 2017, Nghị định 168/2017/NĐ-CP,
Nghị định 94/2021/NĐ-CP (mức ký quỹ kinh doanh dịch vụ lữ hành).
"""

import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

TIMEOUT = 30
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# filename -> {url, title}. Các URL đã kiểm tra truy cập được từ nguồn công khai.
SOURCES = {
    "luat-du-lich-2017.docx": {
        "url": (
            "https://luatvietnam.vn/van-hoa/luat-du-lich-2017-luat-so-09-2017-qh14-115518-d1.html"
        ),
        "title": "Luật Du lịch 2017 (09/2017/QH14)",
    },
    "nghi-dinh-168-2017-nd-cp.docx": {
        "url": (
            "https://luatvietnam.vn/van-hoa/nghi-dinh-168-2017-nd-cp-quy-dinh-chi-tiet-"
            "mot-so-dieu-cua-luat-du-lich-160217-d1.html"
        ),
        "title": "Nghị định 168/2017/NĐ-CP quy định chi tiết một số điều của Luật Du lịch",
    },
    "nghi-dinh-94-2021-nd-cp.docx": {
        "url": "https://dazpro.com/vi/nd-168-2017-ve-du-lich",
        "title": "Nghị định 94/2021/NĐ-CP sửa đổi Điều 14 Nghị định 168/2017/NĐ-CP",
    },
}

BINARY_SUFFIXES = {".pdf", ".doc", ".docx", ".rtf", ".txt"}


class _TextExtractor(HTMLParser):
    """Lấy toàn văn từ trang HTML công khai, bỏ script/style/điều hướng."""

    _SKIP = {"script", "style", "noscript", "header", "footer", "nav", "aside", "form"}
    _BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "li", "br", "tr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "p":
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        raw = "".join(self._parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n\s*\n+", "\n\n", raw)
        return raw.strip()


def extract_html_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text()


def build_docx(text: str, output: Path) -> None:
    """Tạo .docx tối thiểu chứa văn bản (giữ nguyên tiếng Việt)."""
    paragraphs = [paragraph.strip() for paragraph in text.split("\n") if paragraph.strip()]
    xml_paragraphs = [
        '<w:p><w:r><w:t xml:space="preserve">{}</w:t></w:r></w:p>'.format(
            paragraph.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        for paragraph in paragraphs
    ]
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(xml_paragraphs)}</w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.'
        'wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
        'officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)


def setup_directory() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải/tạo ít nhất 3 tài liệu nguồn công khai vào data/landing/legal/."""
    setup_directory()
    for filename, source in SOURCES.items():
        output = DATA_DIR / filename
        if output.exists() and output.stat().st_size > 1024:
            print(f"Skipped (already exists): {output}")
            continue

        url = source["url"]
        suffix = Path(filename).suffix.lower()
        try:
            response = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
            response.raise_for_status()
            if suffix in BINARY_SUFFIXES and url.split("?")[0].lower().endswith(
                tuple(BINARY_SUFFIXES)
            ):
                output.write_bytes(response.content)
                print(f"Downloaded: {output.name}")
            else:
                text = extract_html_text(response.text)
                if len(text) < 1000:
                    raise RuntimeError(f"nội dung quá ngắn ({len(text)} ký tự)")
                build_docx(text, output)
                print(f"Created {output.name} from HTML ({len(text)} ký tự)")
        except Exception as error:  # noqa: BLE001 - báo lỗi rõ cho từng nguồn
            print(f"Failed: {source['title']} — {url}\n  -> {error}")


if __name__ == "__main__":
    setup_directory()
    download_documents()