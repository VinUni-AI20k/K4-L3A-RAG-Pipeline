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


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải ít nhất 3 PDF/DOCX từ nguồn công khai về Thuế Doanh nghiệp."""
    import requests

    sources = {
        "thong_tu_96_2015_tt_btc_thue_tndn.pdf": "https://vbpq.mof.gov.vn/DKC.FileManagement/FileStorage/File/18726",
        "nghi_dinh_123_2020_nd_cp_hoa_don_doanh_nghiep.pdf": "https://vbpq.mof.gov.vn/DKC.FileManagement/FileStorage/File/468129",
        "nghi_dinh_126_2020_nd_cp_quan_ly_thue_doanh_nghiep.pdf": "https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2020/10/32310/33039-1-20201019-1020126-2020-nd-cp.pdf",
        "thong_tu_78_2021_tt_btc_huong_dan_hoa_don_dien_tu.pdf": "https://vbpq.mof.gov.vn/DKC.FileManagement/FileStorage/File/179450",
        "nghi_dinh_91_2022_nd_cp_tam_nop_thue_tndn.pdf": "https://datafiles.chinhphu.vn/cpp/files/duthaovbpl/dt_8c91256f_e36c_4de6_98e7_bc3c0da7544d_20221228152416.pdf",
    }

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for filename, url in sources.items():
        destination = DATA_DIR / filename
        if destination.exists() and destination.stat().st_size > 1024:
            print(f"Skipped (already exists): {filename} ({destination.stat().st_size} bytes)")
            continue

        print(f"Downloading: {filename} from {url} ...")
        response = requests.get(url, headers=headers, timeout=60, verify=False)
        response.raise_for_status()

        if len(response.content) <= 1024:
            raise ValueError(f"Downloaded file {filename} too small: {len(response.content)} bytes")
        if not response.content.startswith(b"%PDF"):
            raise ValueError(f"Downloaded file {filename} is not a valid PDF")

        destination.write_bytes(response.content)
        print(f"Saved: {destination} ({len(response.content)} bytes)")


if __name__ == "__main__":
    setup_directory()
    download_documents()
