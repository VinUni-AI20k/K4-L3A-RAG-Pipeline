"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Hướng dẫn:
    1. Chọn chủ đề của nhóm.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Ví dụ tài liệu: học phí, học bổng, ký túc xá, quy trình đăng ký.
Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

import csv
from pathlib import Path
from urllib.parse import quote


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
MANIFEST = DATA_DIR / "sources.csv"

_BASE = "https://vnulib.edu.vn/images/Tintuc_Thongbao/2026/Dieu chinh chinh sach muon tra TL/"

# filename -> (title, source page, direct PDF url)
SOURCES = {
    "tvtt-thong-bao-106-thay-doi-phi-phuc-vu.pdf": (
        "Thông báo 106/TVTT (18/10/2022) về thay đổi phí phục vụ",
        "https://vnulib.edu.vn/index.php/general/9-tin-tuc-su-kien-thong-bao/428-tb-dieu-chinh-muon-tra-tl-2026",
        _BASE + "18.10.2022-106-TVTT Thay đổi phí phục vụ.pdf",
    ),
    "tvtt-thong-bao-52-dieu-chinh-chinh-sach-muon-tra.pdf": (
        "Thông báo 52/TB (05/03/2026) điều chỉnh chính sách mượn trả tài liệu đối với độc giả tại TVTT",
        "https://vnulib.edu.vn/index.php/general/9-tin-tuc-su-kien-thong-bao/428-tb-dieu-chinh-muon-tra-tl-2026",
        _BASE + "05.3.2026-52-TB-Dieu chinh chinh sach muon tra tai lieu doi voi doc gia tai TVTT.pdf",
    ),
    # PDF có lớp chữ (không phải scan). Là tài liệu hướng dẫn nghiệp vụ của Phòng Phục vụ Độc giả.
    "tvtt-ppv-huong-dan-tra-cuu-muc-luc-truc-tuyen.pdf": (
        "Hướng dẫn tra cứu mục lục trực tuyến (Phòng Phục vụ Độc giả, Thư viện Trung tâm ĐHQG-HCM)",
        "https://vnulib.edu.vn/index.php/cau-hoi-thuong-gap-tai-tvtt",
        "https://vnulib.edu.vn/images/files/PPV_Huong dan tra cuu muc luc truc tuyen.pdf",
    ),
}


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải các PDF chính sách bằng Chromium.

    vnulib.edu.vn thiếu chứng chỉ trung gian nên requests/curl báo lỗi SSL;
    Chromium tự bù chứng chỉ nên tải được mà không phải tắt kiểm tra SSL.
    File đã có thì bỏ qua, chạy lại không tạo bản sao.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(accept_downloads=True)
        for filename, (_, _, url) in SOURCES.items():
            target = DATA_DIR / filename
            if target.exists() and target.stat().st_size > 1024:
                print(f"Exists: {target.name}")
                continue
            page = context.new_page()
            try:
                with page.expect_download(timeout=60_000) as download_info:
                    try:
                        page.goto(quote(url, safe=":/%"), timeout=60_000)
                    except Exception:
                        pass  # Chromium báo "Download is starting" khi URL là file
                download_info.value.save_as(target)
                print(f"Saved: {target.name} ({target.stat().st_size} bytes)")
            except Exception as error:
                print(f"Failed: {url} — {error}")
            finally:
                page.close()
        browser.close()

    write_manifest()


def write_manifest() -> None:
    """Ghi nguồn của từng file để truy vết từ Markdown về URL công khai."""
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["file", "title", "source_page", "pdf_url"])
        for filename, (title, page_url, pdf_url) in SOURCES.items():
            writer.writerow([filename, title, page_url, quote(pdf_url, safe=":/%")])
    print(f"Saved: {MANIFEST}")


if __name__ == "__main__":
    setup_directory()
    download_documents()
