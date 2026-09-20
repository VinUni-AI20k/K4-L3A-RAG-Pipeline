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

from pathlib import Path

import requests


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

# Chủ đề: Pháp luật cho hộ kinh doanh.
# Nguồn: Cổng thông tin điện tử Chính phủ (chinhphu.vn) — chính thức, không cần đăng nhập.
# Đã kiểm tra hiệu lực tại thời điểm thu thập (09/2026):
#   - NĐ 01/2021/NĐ-CP đã hết hiệu lực (thay bằng NĐ 168/2025/NĐ-CP từ 01/7/2025).
#   - NĐ 52/2013/NĐ-CP đã hết hiệu lực (thay bằng Luật TMĐT 122/2025/QH15 từ 01/7/2026).
#
# Mỗi văn bản có 2 file: bản .pdf ký số (ảnh scan, không có lớp text — giữ làm bằng
# chứng nguồn gốc) và bản .doc/.docx đánh máy lại do Công báo Chính phủ phát hành
# (dùng để convert markdown ở Task 3, tránh lỗi OCR trên số liệu pháp lý).
SOURCES = {
    "nghi-dinh-168-2025-nd-cp-dang-ky-ho-kinh-doanh.pdf": (
        "https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/7/168nd.signed.pdf"
    ),
    "nghi-dinh-168-2025-nd-cp-dang-ky-ho-kinh-doanh.doc": (
        "https://g7.cdnchinhphu.vn/api/download/stream?Url=tm-8mq6BhNw0NbrKRhTDAQWsKg3tuqaY0aWypnY78U6M2BY68Ekp0Gvvr483flbRj1RyLBgY4fo6pGjduHp6Qa7R_hN6zLj1G-vfAfcysY7aFGerqwsRGV_YHJL073HdWlO7xLrsUbpyWNW10ADG_Q~~&file_name=2025_885+%2b+886_168-2025-N%c4%90-CP.doc"
    ),
    "nghi-dinh-70-2025-nd-cp-sua-doi-hoa-don-chung-tu.pdf": (
        "https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/3/70-nd-cp.signed.pdf"
    ),
    "nghi-dinh-70-2025-nd-cp-sua-doi-hoa-don-chung-tu.doc": (
        "https://g7.cdnchinhphu.vn/api/download/stream?Url=tm-8mq6BhNw0NbrKRhTDAQWsKg3tuqaY0aWypnY78U6M2BY68Ekp0Gvvr483flbRtfNlH72Kgn5xZd60NyPfX56Um8U4Gr8qUNveVw9j6QM22ktcgg4pwu_iVJ_awYVK9gp26im9ajgIIaPpQ0l-ZQ~~&file_name=2025_613+%2b+614_70-2025-N%c4%90-CP.doc"
    ),
    "nghi-quyet-198-2025-qh15-kinh-te-tu-nhan.pdf": (
        "https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/5/198_nq.pdf"
    ),
    "nghi-quyet-198-2025-qh15-kinh-te-tu-nhan.doc": (
        "https://g7.cdnchinhphu.vn/api/download/stream?Url=tm-8mq6BhNw0NbrKRhTDAQWsKg3tuqaY0aWypnY78U6M2BY68Ekp0Gvvr483flbRgjdm6ATDW6lYNuyRefVjvJx8b7puPQK51GatMuyP4fYJCsc0uqabQX5IJeoROY63FRZutsttHCdP_k8y6GTtoQ~~&file_name=2025_713+%2b+714_198-2025-QH15.doc"
    ),
    "luat-122-2025-qh15-thuong-mai-dien-tu.pdf": (
        "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/01/luat122.2025.qh15.pdf"
    ),
    "luat-122-2025-qh15-thuong-mai-dien-tu.docx": (
        "https://g7.cdnchinhphu.vn/api/download/stream?Url=tm-8mq6BhNw0NbrKRhTDAaHMpvrqWaeHuYm7lW3HNfzTzww8Myg35dDL_fJB4izwdTmY8lT_ztXn8sjqamdtgK0oZCx4FXKnKkaJRoOXGcPNKOUgUTrnMhnpfM_PNkCT&file_name=2026_41_122%2f2025%2fQH15.docx"
    ),
}

# g7.cdnchinhphu.vn (bản .doc/.docx) trả chuỗi chứng chỉ TLS không đầy đủ; datafiles.chinhphu.vn
# (bản .pdf) thì bình thường. Đây là văn bản công khai, rủi ro thấp nên tắt verify riêng cho domain này.
INSECURE_HOSTS = {"g7.cdnchinhphu.vn"}


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải ít nhất 3 PDF/DOCX từ nguồn công khai."""
    for filename, url in SOURCES.items():
        destination = DATA_DIR / filename
        if destination.exists() and destination.stat().st_size > 1024:
            print(f"Skip (exists): {destination}")
            continue
        verify = not any(host in url for host in INSECURE_HOSTS)
        response = requests.get(
            url,
            timeout=(30, 120),
            headers={"User-Agent": "Mozilla/5.0"},
            stream=True,
            verify=verify,
        )
        response.raise_for_status()
        with destination.open("wb") as file_handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                file_handle.write(chunk)
        print(f"Saved: {destination} ({destination.stat().st_size} bytes)")


if __name__ == "__main__":
    setup_directory()
    download_documents()
