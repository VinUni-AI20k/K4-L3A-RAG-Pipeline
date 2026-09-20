"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Hướng dẫn:
    1. Chọn chủ đề của nhóm: Du lịch Việt Nam.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Ví dụ tài liệu: học phí, học bổng, ký túc xá, quy trình đăng ký.
Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

from pathlib import Path
import requests

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

# Danh sách mapping đổi tên các file tải thủ công sang không dấu chuẩn
RENAME_MAP = {
    "Luật-09-2017-QH14.doc": "luat_du_lich_2017.doc",
    "Nghị-định-45-2019-NĐ-CP.doc": "nghi_dinh_45_2019_nd_cp.doc",
    "Thông-tư-06-2017-TT-BVHTTDL.doc": "thong_tu_06_2017_tt_bvhttdl.doc",
}

# Nguồn online dự phòng (nếu chạy trên máy chưa có file)
ONLINE_SOURCES = {
    "luat_du_lich_2017.doc": "https://luatvietnam.vn/van-ban/tai-file-e8ed0b93-0569-1600-9297-f38b2b18931e",
    "nghi_dinh_45_2019_nd_cp.doc": "https://luatvietnam.vn/van-ban/tai-file-21f85654-057a-be00-66f2-2224771d3f54",
    "thong_tu_06_2017_tt_bvhttdl.doc": "https://luatvietnam.vn/van-ban/tai-file-31d9e9df-04e7-8d00-9488-2cbbf635c82e",
}


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[Setup] Ready: {DATA_DIR}")


def standardize_existing_files() -> None:
    """Đổi tên các file có dấu đã tải thủ công sang định dạng không dấu."""
    for old_name, new_name in RENAME_MAP.items():
        old_file = DATA_DIR / old_name
        new_file = DATA_DIR / new_name
        if old_file.exists():
            old_file.rename(new_file)
            print(f"[Rename] {old_name} -> {new_name}")


def download_documents() -> None:
    """Tải hoặc kiểm tra ít nhất 3 tài liệu pháp lý."""
    # 1. Chuẩn hóa các file đã tải sẵn
    standardize_existing_files()

    # 2. Tải bổ sung từ URL nếu máy chạy chưa có file
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for filename, url in ONLINE_SOURCES.items():
        file_path = DATA_DIR / filename
        if not file_path.exists():
            print(f"[Download] Đang tải {filename}...")
            try:
                response = requests.get(url, headers=headers, timeout=30, verify=False)
                response.raise_for_status()
                file_path.write_bytes(response.content)
                print(f"[Success] Đã lưu: {filename}")
            except Exception as e:
                print(f"[Warning] Không thể tự động tải {filename} ({e}). Hãy đảm bảo file đã được copy thủ công vào thư mục.")

    # 3. Kiểm tra số lượng file hợp lệ (.pdf, .doc, .docx)
    valid_extensions = {".pdf", ".doc", ".docx"}
    current_files = [f for f in DATA_DIR.iterdir() if f.suffix.lower() in valid_extensions]

    print(f"\n[Summary] Đã tìm thấy {len(current_files)} văn bản hợp lệ:")
    for f in current_files:
        print(f" - {f.name}")

    if len(current_files) < 3:
        raise ValueError(f"Cần tối thiểu 3 file PDF/DOCX, hiện tại chỉ có {len(current_files)} file!")
    print("\n[OK] Hoàn thành Task 1!")


if __name__ == "__main__":
    setup_directory()
    download_documents()