"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Chủ đề: Trợ lý Pháp luật & Quy chế Đào tạo Đại học, Sau đại học và Chuẩn Chương trình Đào tạo
Tài liệu cốt lõi:
1. Luật số 125/2025/QH15 (Luật Giáo dục đại học)
2. Thông tư 54/2026/TT-BGDĐT (Chuẩn chương trình đào tạo các trình độ của giáo dục đại học)
3. Thông tư 56/2026/TT-BGDĐT (Quy chế đào tạo trình độ đại học)
4. Thông tư 53/2026/TT-BGDĐT (Quy chế tuyển sinh và đào tạo sau đại học: thạc sĩ, tiến sĩ)
5. Thông tư 07/2025/TT-BGDĐT (Liên kết đào tạo với cơ sở giáo dục đại học nước ngoài)
6. Quyết định 678/QĐ-BGDĐT (Chuẩn CTĐT lĩnh vực Pháp luật trình độ đại học)
7. Quyết định 2627/QĐ-BGDĐT (Chuẩn CTĐT kỹ sư, thạc sĩ tài năng các lĩnh vực STEM)
8. Quyết định 1169/QĐ-BGDĐT (Chuẩn CTĐT khối ngành Kiến trúc - Xây dựng trình độ đại học)
9. Quyết định 2333/QĐ-BGDĐT (Chuẩn CTĐT lĩnh vực Môi trường và bảo vệ môi trường trình độ đại học)
10. Quyết định 2101/QĐ-BGDĐT (Sửa đổi chuẩn CTĐT vi mạch bán dẫn trình độ đại học, thạc sĩ)
"""

from pathlib import Path
import requests

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

LEGAL_SOURCES = {
    "luat_125_2025_QH15_giao_duc_dai_hoc.pdf": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/12/125-qh15.pdf",
    "thong_tu_54_2026_TT_BGDDT_chuong_trinh_dao_tao.pdf": "https://moet.gov.vn/van-ban/vbdh/Pages/chi-tiet-van-ban.aspx?ItemID=54-2026",
    "thong_tu_56_2026_TT_BGDDT_quy_che_dao_tao_dai_hoc.pdf": "https://moet.gov.vn/van-ban/vbdh/Pages/chi-tiet-van-ban.aspx?ItemID=56-2026",
    "thong_tu_53_2026_TT_BGDDT_tuyen_sinh_sau_dai_hoc.pdf": "https://moet.gov.vn/van-ban/vbdh/Pages/chi-tiet-van-ban.aspx?ItemID=53-2026",
    "thong_tu_07_2025_TT_BGDDT_lien_ket_quoc_te.pdf": "https://moet.gov.vn/van-ban/vbdh/Pages/chi-tiet-van-ban.aspx?ItemID=07-2025",
    "quyet_dinh_678_2025_QD_BGDDT_chuan_ctdt_phap_luat.pdf": "https://moet.gov.vn/van-ban/vbdh/Pages/chi-tiet-van-ban.aspx?ItemID=678-2025",
    "quyet_dinh_2627_2025_QD_BGDDT_chuan_ctdt_tai_nang_stem.pdf": "https://moet.gov.vn/van-ban/vbdh/Pages/chi-tiet-van-ban.aspx?ItemID=2627-2025",
    "quyet_dinh_1169_2026_QD_BGDDT_chuan_ctdt_kien_truc_xay_dung.pdf": "https://moet.gov.vn/van-ban/vbdh/Pages/chi-tiet-van-ban.aspx?ItemID=1169-2026",
    "quyet_dinh_2333_2025_QD_BGDDT_chuan_ctdt_moi_truong.pdf": "https://moet.gov.vn/van-ban/vbdh/Pages/chi-tiet-van-ban.aspx?ItemID=2333-2025",
    "quyet_dinh_2101_2025_QD_BGDDT_sua_doi_chuan_ctdt_vi_mach_ban_dan.pdf": "https://moet.gov.vn/van-ban/vbdh/Pages/chi-tiet-van-ban.aspx?ItemID=2101-2025",
}


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải ít nhất 3 PDF từ nguồn công khai chính thức."""
    setup_directory()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    for filename, url in LEGAL_SOURCES.items():
        file_path = DATA_DIR / filename
        if file_path.exists() and file_path.stat().st_size > 1024:
            print(f"Already exists: {filename} ({file_path.stat().st_size} bytes)")
            continue

        try:
            print(f"Downloading {filename} from {url}...")
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200 and len(response.content) > 1024:
                file_path.write_bytes(response.content)
                print(f"Saved: {filename} ({len(response.content)} bytes)")
            else:
                print(f"Download returned status {response.status_code}, keeping existing local file if valid.")
        except Exception as e:
            print(f"Could not download {filename}: {e}. Using existing file.")


if __name__ == "__main__":
    download_documents()
