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
    """Tải ít nhất 3 PDF/DOCX từ nguồn công khai."""
    import requests

    sources = {
        "quy_che_dao_tao_dhqghn_3626.pdf": "https://ussh.vnu.edu.vn/vi/van-ban/detail/Quy-che-dao-tao-dai-hoc-tai-Dai-hoc-Quoc-gia-Ha-Noi-Ap-dung-tu-khoa-QH-2022-X-19452/?download=1&id=0",
        "quy_dinh_hoc_bong_dhqghn_4618.pdf": "https://ussh.vnu.edu.vn/uploads/ussh/van-ban/qd4618cong-tac-qua-ly-va-su-dung-hoc-bong-tai-dhqghn.pdf",
        "quy_trinh_canh_bao_hoc_vu_dhqghn.pdf": "https://daotao.ulis.vnu.edu.vn/files/uploads/2024/11/Q%C4%902244-06.11.2024_Q%C4%90-ban-h%C3%A0nh-quy-tr%C3%ACnh-x%C3%A9t-CBHV-ban-h%C3%A0nh.pdf",
    }



    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for filename, url in sources.items():
        destination = DATA_DIR / filename
        if destination.exists() and destination.stat().st_size > 1024:
            print(f"Skipped (already exists): {destination.name} ({destination.stat().st_size:,} bytes)")
            continue

        print(f"Downloading: {filename} from {url}...")
        try:
            with requests.get(url, headers=headers, stream=True, timeout=60, verify=False) as response:
                response.raise_for_status()
                with open(destination, "wb") as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
            print(f"Downloaded: {destination.name} ({destination.stat().st_size:,} bytes)")
        except Exception as error:
            print(f"Failed to download {filename}: {error}")
            if destination.exists():
                destination.unlink(missing_ok=True)
            raise


if __name__ == "__main__":
    setup_directory()
    download_documents()

