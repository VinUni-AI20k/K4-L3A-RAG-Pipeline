"""
Task 1 — Thu thập văn bản pháp luật về du lịch Việt Nam.

Script có thể chạy lại nhiều lần. File hợp lệ đã tồn tại sẽ được giữ nguyên;
file thiếu hoặc không hợp lệ sẽ được tải lại từ Cổng Thông tin điện tử Chính
phủ. Tất cả tên file đều không dấu để thuận tiện cho các bước xử lý tiếp theo.
"""

from pathlib import Path
from typing import Final

import requests


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
MIN_DOCUMENT_SIZE: Final = 1024
DOWNLOAD_TIMEOUT: Final = (10, 60)

# Nguồn chính thức: Cổng Thông tin điện tử Chính phủ.
DOCUMENT_SOURCES: Final = {
    "luat_du_lich_09_2017_qh14.pdf": (
        "https://datafiles.chinhphu.vn/cpp/files/vbpq/2017/07/09.signed.pdf"
    ),
    "nghi_dinh_168_2017_nd_cp_huong_dan_luat_du_lich.pdf": (
        "https://datafiles.chinhphu.vn/cpp/files/vbpq/2018/03/168.signed.pdf"
    ),
    "quyet_dinh_147_qd_ttg_chien_luoc_phat_trien_du_lich_2030.pdf": (
        "https://datafiles.chinhphu.vn/cpp/files/vbpq/2020/01/147.signed.pdf"
    ),
}


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def validate_pdf(path: Path) -> None:
    """Kiểm tra tối thiểu để loại file rỗng hoặc trang lỗi giả dạng PDF."""
    if not path.is_file():
        raise ValueError(f"Không tìm thấy tài liệu: {path}")
    if path.stat().st_size <= MIN_DOCUMENT_SIZE:
        raise ValueError(f"Tài liệu quá nhỏ hoặc rỗng: {path}")
    with path.open("rb") as file:
        if file.read(5) != b"%PDF-":
            raise ValueError(f"Tài liệu không phải PDF hợp lệ: {path}")


def _is_valid_pdf(path: Path) -> bool:
    try:
        validate_pdf(path)
    except (OSError, ValueError):
        return False
    return True


def _download_pdf(url: str, destination: Path) -> None:
    """Tải vào file tạm và chỉ thay file đích sau khi kiểm tra thành công."""
    temporary_path = destination.with_suffix(destination.suffix + ".part")
    try:
        with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as response:
            response.raise_for_status()
            with temporary_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        file.write(chunk)
        validate_pdf(temporary_path)
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def download_documents() -> list[Path]:
    """Bảo đảm ba tài liệu chính thức có mặt và trả về các đường dẫn."""
    setup_directory()
    documents: list[Path] = []

    for filename, url in DOCUMENT_SOURCES.items():
        destination = DATA_DIR / filename
        if _is_valid_pdf(destination):
            print(f"Đã có: {filename}")
        else:
            print(f"Đang tải: {filename}")
            try:
                _download_pdf(url, destination)
            except (OSError, requests.RequestException, ValueError) as error:
                raise RuntimeError(f"Không thể tải {filename} từ {url}") from error
            print(f"Đã tải: {filename}")

        validate_pdf(destination)
        documents.append(destination)

    print(f"Hoàn tất: {len(documents)} tài liệu hợp lệ tại {DATA_DIR}")
    return documents


if __name__ == "__main__":
    download_documents()
