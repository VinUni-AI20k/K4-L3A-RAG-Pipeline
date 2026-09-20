"""
Task 1 — Thu thập tài liệu chính sách/quy định về du lịch Việt Nam.

Nguồn đều là cổng thông tin công khai của cơ quan nhà nước (Cục Du lịch Quốc gia,
UBND/Sở VHTTDL các tỉnh). Downloader idempotent: file đã tải hợp lệ thì bỏ qua,
nên chạy lại pipeline không tạo bản sao.

Lưu ý: nhiều cổng thông tin trả HTTP 200 kèm trang HTML báo lỗi thay vì file thật,
nên phải kiểm tra magic bytes chứ không tin status code.
"""

from pathlib import Path

import requests


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

# Kích thước tối thiểu để loại trang lỗi ngắn bị trả nhầm thành file.
MIN_SIZE_BYTES = 10 * 1024
TIMEOUT_SECONDS = 60

# Magic bytes hợp lệ: %PDF- cho PDF, PK cho DOCX (zip container).
VALID_SIGNATURES = (b"%PDF-", b"PK\x03\x04")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

SOURCES: dict[str, str] = {
    "quy-hoach-he-thong-du-lich-2021-2030.pdf": (
        "https://images.vietnamtourism.gov.vn/vn//dmdocuments/2022/"
        "220925_BCTT_QHHTDL.pdf"
    ),
    "de-an-phat-trien-san-pham-du-lich-dem.pdf": (
        "https://images.vietnamtourism.gov.vn/vn/dmdocuments/2023/"
        "3.de_an_dl_dem.pdf"
    ),
    "du-thao-nghi-dinh-huong-dan-luat-du-lich.pdf": (
        "https://images.vietnamtourism.gov.vn/vn/dmdocuments/"
        "Du-thao-Nghi-dinh-Dang-tai.pdf"
    ),
    "bao-cao-thi-hanh-luat-du-lich-2017.pdf": (
        "https://datafiles.nghean.gov.vn/nan-ubnd/2897/quantritintuc202411/"
        "bao_cao_tong_hop_thi_hanh_luat20241011024147758_Signed.pdf"
    ),
}


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def is_valid_document(payload: bytes) -> bool:
    """Kiểm tra payload là PDF/DOCX thật, không phải trang HTML trả nhầm."""
    return len(payload) >= MIN_SIZE_BYTES and payload.startswith(VALID_SIGNATURES)


def download_one(filename: str, url: str) -> bool:
    """Tải một tài liệu; trả về True khi file hợp lệ đã sẵn sàng trên đĩa."""
    target = DATA_DIR / filename

    if target.exists() and is_valid_document(target.read_bytes()):
        print(f"Skip (đã có): {filename}")
        return True

    try:
        response = requests.get(
            url,
            timeout=TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"Failed: {filename} — {error}")
        return False

    payload = response.content
    if not is_valid_document(payload):
        preview = payload[:5].decode("latin-1", errors="replace")
        print(
            f"Rejected: {filename} — không phải PDF/DOCX "
            f"(magic={preview!r}, {len(payload)} bytes, "
            f"content-type={response.headers.get('Content-Type')})"
        )
        return False

    target.write_bytes(payload)
    print(f"Saved: {filename} ({len(payload) / 1024:.0f} KB)")
    return True


def download_documents() -> None:
    """Tải toàn bộ tài liệu chính sách trong SOURCES."""
    succeeded = sum(download_one(name, url) for name, url in SOURCES.items())
    print(f"\n{succeeded}/{len(SOURCES)} tài liệu hợp lệ trong {DATA_DIR}")
    if succeeded < 3:
        print("Cảnh báo: cần tối thiểu 3 tài liệu để pass acceptance test.")


if __name__ == "__main__":
    setup_directory()
    download_documents()
