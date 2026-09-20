"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Chủ đề nhóm: Luật giao thông đường bộ Việt Nam.

Nguồn: Công báo điện tử (congbao.chinhphu.vn) và kho văn bản
datafiles.chinhphu.vn — đều là nguồn công khai của Chính phủ.

Hai cái bẫy của nguồn này, download_documents() kiểm tra cả hai:
    1. Bản "signed" trên datafiles.chinhphu.vn của nhiều nghị định là ảnh scan,
       không có text layer nên PDF parser đọc ra 0 ký tự.
    2. Văn bản dài được Công báo đăng làm nhiều số; mỗi số là một file PDF riêng
       và file không phải số cuối kết thúc bằng "(Xem tiếp Công báo số ...)".
       Chỉ tải file đầu tiên là mất phần lớn nội dung — ví dụ Luật 36/2024/QH15
       có 89 điều nhưng file phần 1 chỉ tới Điều 23.
"""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import date
from pathlib import Path

import requests
import truststore


# CDN của chinhphu.vn không gửi kèm intermediate certificate nên bundle certifi
# mặc định sẽ báo CERTIFICATE_VERIFY_FAILED; dùng trust store của hệ điều hành.
truststore.inject_into_ssl()


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
MANIFEST_PATH = DATA_DIR / "sources.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; K4-RAG-lab/0.1)"}
MIN_BYTES = 1024
TIMEOUT = 120

# Link file trên trang Công báo trỏ tới CDN, cần bóc ra từ HTML.
PDF_LINK_PATTERN = re.compile(r'href="([^"]*cdnchinhphu[^"]*\.pdf[^"]*)"', re.IGNORECASE)

# stem: đặt không dấu và thể hiện đúng nội dung văn bản. Văn bản đăng nhiều số
#       Công báo sẽ thành <stem>-phan-1.pdf, <stem>-phan-2.pdf...
# page: trang công khai dùng để trích dẫn và kiểm chứng lại.
# file: link tải trực tiếp; để None khi phải bóc link từ trang Công báo.
SOURCES = [
    {
        "stem": "luat-36-2024-qh15-trat-tu-an-toan-giao-thong-duong-bo",
        "title": "Luật Trật tự, an toàn giao thông đường bộ số 36/2024/QH15",
        "doc_no": "36/2024/QH15",
        "page": "https://congbao.chinhphu.vn/van-ban/luat-so-36-2024-qh15-42555.htm",
        "file": None,
    },
    {
        "stem": "vbhn-49-vbhn-vpqh-luat-duong-bo",
        "title": "Văn bản hợp nhất số 49/VBHN-VPQH hợp nhất Luật Đường bộ (Luật số 35/2024/QH15)",
        "doc_no": "49/VBHN-VPQH",
        "page": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/3/49-vbhn-vpqh.pdf",
        "file": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/3/49-vbhn-vpqh.pdf",
    },
    {
        "stem": "nd-151-2024-huong-dan-luat-trat-tu-an-toan-giao-thong-duong-bo",
        "title": (
            "Nghị định số 151/2024/NĐ-CP quy định chi tiết một số điều và biện pháp "
            "thi hành Luật Trật tự, an toàn giao thông đường bộ"
        ),
        "doc_no": "151/2024/NĐ-CP",
        "page": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-151-2024-nd-cp-43411.htm",
        "file": None,
    },
    {
        "stem": "nd-158-2024-hoat-dong-van-tai-duong-bo",
        "title": "Nghị định số 158/2024/NĐ-CP quy định về hoạt động vận tải đường bộ",
        "doc_no": "158/2024/NĐ-CP",
        "page": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-158-2024-nd-cp-43540/53503.htm",
        "file": None,
    },
    {
        "stem": "nd-165-2024-huong-dan-luat-duong-bo",
        "title": (
            "Nghị định số 165/2024/NĐ-CP quy định chi tiết, hướng dẫn thi hành một số "
            "điều của Luật Đường bộ và Điều 77 Luật Trật tự, an toàn giao thông đường bộ"
        ),
        "doc_no": "165/2024/NĐ-CP",
        "page": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-165-2024-nd-cp-43729.htm",
        "file": None,
    },
    {
        "stem": "nd-168-2024-xu-phat-vi-pham-giao-thong-duong-bo",
        "title": (
            "Nghị định số 168/2024/NĐ-CP quy định xử phạt vi phạm hành chính về trật tự, "
            "an toàn giao thông trong lĩnh vực giao thông đường bộ; trừ điểm, phục hồi "
            "điểm giấy phép lái xe"
        ),
        "doc_no": "168/2024/NĐ-CP",
        "page": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-168-2024-nd-cp-43733.htm",
        "file": None,
    },
]


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def resolve_file_urls(source: dict) -> list[str]:
    """Trả về link tải của mọi phần; bóc từ trang Công báo khi chưa có link."""
    if source["file"]:
        return [source["file"]]

    response = requests.get(source["page"], headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    links = [html.unescape(link) for link in PDF_LINK_PATTERN.findall(response.text)]
    if not links:
        raise RuntimeError(f"Không tìm thấy link PDF trong trang: {source['page']}")
    return links


def count_text_chars(path: Path, pages: int = 3) -> int:
    """Đếm ký tự trích xuất được từ vài trang đầu để phát hiện PDF scan."""
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return sum(len(page.extract_text() or "") for page in pdf.pages[:pages])


def has_continuation_marker(path: Path) -> bool:
    """True khi trang cuối còn dòng "(Xem tiếp Công báo số ...)" tức thiếu phần sau."""
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        tail = pdf.pages[-1].extract_text() or ""
    return "Xem tiếp Công báo" in tail


def download_part(url: str, target: Path) -> None:
    """Tải một file PDF và kiểm tra sơ bộ nội dung."""
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()

    if not response.content.startswith(b"%PDF"):
        raise RuntimeError(f"Nội dung tải về không phải PDF: {url}")
    if len(response.content) <= MIN_BYTES:
        raise RuntimeError(f"File tải về quá nhỏ: {url}")

    target.write_bytes(response.content)
    print(f"Saved: {target.name} ({len(response.content) // 1024} KB)")


def download_documents() -> None:
    """Tải tài liệu công khai vào data/landing/legal/ và ghi manifest nguồn."""
    manifest = []

    for source in SOURCES:
        urls = resolve_file_urls(source)
        total = len(urls)

        for index, url in enumerate(urls, 1):
            suffix = "" if total == 1 else f"-phan-{index}"
            target = DATA_DIR / f"{source['stem']}{suffix}.pdf"

            if target.exists() and target.stat().st_size > MIN_BYTES:
                print(f"Skip (đã có): {target.name}")
            else:
                download_part(url, target)

            text_chars = count_text_chars(target)
            if text_chars == 0:
                print(f"  CẢNH BÁO: {target.name} không có text layer (bản scan).")
            else:
                print(f"  Text layer OK ({text_chars} ký tự / 3 trang đầu)")

            if index == total and has_continuation_marker(target):
                print(f"  CẢNH BÁO: {target.name} vẫn còn 'Xem tiếp Công báo' — thiếu phần sau.")

            title = source["title"] if total == 1 else f"{source['title']} (phần {index}/{total})"
            manifest.append(
                {
                    "filename": target.name,
                    "title": title,
                    "doc_no": source["doc_no"],
                    "url": source["page"],
                    "part": index,
                    "part_count": total,
                    "date_downloaded": date.today().isoformat(),
                    "text_chars_sampled": text_chars,
                }
            )

    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    # Console Windows mặc định là cp1252 nên print tiếng Việt sẽ crash.
    if (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    setup_directory()
    download_documents()
