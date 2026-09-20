"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Chủ đề: Du lịch Việt Nam.
Tự động đăng nhập LuatVietnam qua Playwright với selector linh hoạt.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

SOURCES = {
    "luat_du_lich_2017.doc": "https://luatvietnam.vn/van-ban/tai-file-e8ed0b93-0569-1600-9297-f38b2b18931e",
    "nghi_dinh_45_2019_nd_cp.doc": "https://luatvietnam.vn/van-ban/tai-file-21f85654-057a-be00-66f2-2224771d3f54",
    "thong_tu_06_2017_tt_bvhttdl.doc": "https://luatvietnam.vn/van-ban/tai-file-31d9e9df-04e7-8d00-9488-2cbbf635c82e",
}


def setup_directory() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[Setup] Ready: {DATA_DIR}")


def fill_input(page, candidate_selectors, value: str, field_name: str) -> bool:
    """Thử lần lượt các selector khả dĩ cho ô nhập liệu."""
    for sel in candidate_selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=3000):
                loc.fill(value)
                print(f" -> Đã điền {field_name} qua selector: {sel}")
                return True
        except Exception:
            continue
    return False


def download_with_playwright() -> None:
    username = os.getenv("LUATVIETNAM_USERNAME")
    password = os.getenv("LUATVIETNAM_PASSWORD")

    if not username or not password:
        raise ValueError("Vui lòng khai báo LUATVIETNAM_USERNAME và LUATVIETNAM_PASSWORD trong file .env!")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            accept_downloads=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
        )
        page = context.new_page()

        print("[Browser] Đang mở trang đăng nhập LuatVietnam...")
        page.goto("https://luatvietnam.vn/user/dang-nhap-tai-khoan.html", wait_until="domcontentloaded", timeout=60000)

        # Danh sách selector khả dĩ cho trường username/email
        user_selectors = [
            "input[type='email']",
            "input[name='CustomerName']",
            "input[name='UserName']",
            "input[name='email']",
            "input[placeholder*='Email']",
            "input[placeholder*='Tên đăng nhập']",
            "input[placeholder*='Số điện thoại']",
            "#CustomerName",
            "#UserName",
            "#Email",
        ]

        # Danh sách selector khả dĩ cho trường password
        pwd_selectors = [
            "input[type='password']",
            "input[name='CustomerPassword']",
            "input[name='Password']",
            "#CustomerPassword",
            "#Password",
        ]

        # Nút submit
        submit_selectors = [
            "button[type='submit']",
            "button:has-text('Đăng nhập')",
            "input[type='submit']",
            ".btn-login",
            "#btnLogin",
        ]

        print(f"[Auth] Đang điền tài khoản: {username}...")
        filled_user = fill_input(page, user_selectors, username, "Username")
        filled_pwd = fill_input(page, pwd_selectors, password, "Password")

        if not (filled_user and filled_pwd):
            # Lưu ảnh chụp màn hình để debug nếu không tìm thấy ô nhập liệu
            page.screenshot(path="login_debug.png")
            raise RuntimeError("Không tìm thấy ô nhập tài khoản/mật khẩu. Đã chụp ảnh màn hình lưu tại login_debug.png")

        # Bấm submit
        clicked = False
        for s_sel in submit_selectors:
            try:
                btn = page.locator(s_sel).first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            page.keyboard.press("Enter")

        # Chờ điều hướng xong
        page.wait_for_timeout(4000)
        print("[Auth] Đã gửi thông tin đăng nhập.")

        print("\n--- Bắt đầu tải tài liệu ---")
        for filename, url in SOURCES.items():
            dest_path = DATA_DIR / filename
            print(f"[Downloading] {filename}...")
            try:
                with page.expect_download(timeout=45000) as download_info:
                    page.goto(url)

                download = download_info.value
                download.save_as(str(dest_path))

                file_size_kb = dest_path.stat().st_size / 1024
                print(f" -> [OK] Đã lưu: {filename} ({file_size_kb:.1f} KB)")
            except Exception as e:
                # Nếu không tự kích hoạt download, kiểm tra xem có nút bấm tải trên trang không
                try:
                    btn = page.query_selector("a[href*='tai-file'], button:has-text('Tải về'), .btn-download")
                    if btn:
                        with page.expect_download(timeout=30000) as download_info:
                            btn.click()
                        download = download_info.value
                        download.save_as(str(dest_path))
                        print(f" -> [OK] Đã tải qua nút bấm: {filename}")
                    else:
                        print(f" -> [Lỗi {filename}]: {e}")
                except Exception as err2:
                    print(f" -> [Lỗi {filename}]: {err2}")

        browser.close()

    # Kiểm tra tổng kết
    valid_files = [
        f for f in DATA_DIR.iterdir()
        if f.suffix.lower() in {".doc", ".docx", ".pdf"} and f.stat().st_size > 1024
    ]

    print(f"\n[Summary] Đã có {len(valid_files)} file hợp lệ trong {DATA_DIR}:")
    for f in valid_files:
        print(f" - {f.name} ({f.stat().st_size // 1024} KB)")

    if len(valid_files) < 3:
        raise RuntimeError(f"Chưa đủ 3 file hợp lệ (hiện có {len(valid_files)}).")

    print("\n[Complete] Hoàn thành Task 1!")


if __name__ == "__main__":
    setup_directory()
    download_with_playwright()