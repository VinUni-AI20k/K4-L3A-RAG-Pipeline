import os
import csv
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

load_dotenv()

def login_via_popup(page, username: str, password: str) -> None:
    print("[Auth] Mở trang chủ...")
    page.goto("https://luatvietnam.vn/", wait_until="domcontentloaded")

    try:
        login_button = page.locator("span.btn-login.btn-auth[data-tab='login']").first
        login_button.wait_for(state="visible", timeout=5000)
        login_button.click()
        print("[Auth] Đã click nút mở form. Đợi Iframe load...")

        frame = page.frame_locator("iframe[title='LuatVietnam Single Sign On']")
        username_input = frame.locator("input[id='login.CustomerName']")
        password_input = frame.locator("input[id='Password']")
        
        username_input.wait_for(state="visible", timeout=10000)

        print("[Auth] Đang nhập username và password...")
        username_input.fill(username)
        password_input.fill(password)

        print("[Auth] Nhấn phím Enter để submit...")
        password_input.press("Enter")
        
        page.locator("#authPopup").wait_for(state="hidden", timeout=10000)
        print("[Auth] Đã đăng nhập thành công!")

    except Exception as e:
        print(f"[LỖI] Quá trình đăng nhập thất bại:\n{e}")
        raise

def download_documents(page, docs: list, output_dir: Path) -> None:
    # Tạo thư mục chứa file nếu chưa có
    output_dir.mkdir(parents=True, exist_ok=True)

    for doc in docs:
        short_name = doc['short_name'].strip()
        url = doc['url'].strip()
        
        print(f"\n[Download] Xử lý tài liệu: {short_name}")
        print(f" -> Truy cập: {url}")
        page.goto(url, wait_until="domcontentloaded")

        try:
            vn_doc_area = page.locator("div.vn-doc")
            vn_doc_area.wait_for(state="attached", timeout=10000)

            doc_link = vn_doc_area.locator("a[href*='/tai-file'][title*='doc']").first
            pdf_link = vn_doc_area.locator("a[href*='/tai-file'][title*='pdf']").first

            target_link = None
            if doc_link.count() > 0:
                target_link = doc_link
                print(" -> Tìm thấy bản Tiếng Việt (Word). Đang tải...")
            elif pdf_link.count() > 0:
                target_link = pdf_link
                print(" -> Không có bản Word, tìm thấy bản Tiếng Việt (PDF). Đang tải...")
            else:
                print(" -> [Bỏ qua] Không tìm thấy link tải định dạng Word/PDF Tiếng Việt.")
                continue

            with page.expect_download(timeout=15000) as download_info:
                target_link.evaluate("el => el.click()")
            
            download = download_info.value
            
            # Lấy đuôi file gốc (.doc, .docx, .pdf) để ghép với short_name
            original_ext = os.path.splitext(download.suggested_filename)[1]
            final_file_name = f"{short_name}{original_ext}"
            file_path = output_dir / final_file_name
            
            download.save_as(file_path)
            print(f" -> Tải và lưu thành công: {file_path}")

        except PlaywrightTimeoutError:
            print(f" -> [LỖI TIMEOUT] Không tìm thấy khu vực tải tài liệu Tiếng Việt.")
        except Exception as e:
            print(f" -> [LỖI] Lỗi khi tải file: {e}")

def main():
    username = os.getenv("LUATVIETNAM_USERNAME")
    password = os.getenv("LUATVIETNAM_PASSWORD")

    if not username or not password:
        raise ValueError("Vui lòng khai báo LUATVIETNAM_USERNAME và LUATVIETNAM_PASSWORD trong file .env!")

    BASE_DIR = Path(__file__).resolve().parent.parent
    
    INPUT_CSV = BASE_DIR / "legal_urls.csv"
    OUTPUT_DIR = BASE_DIR / "data" / "landing" / "legal"

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Không tìm thấy file danh sách link tại: {INPUT_CSV}")

    docs_to_download = []
    with open(INPUT_CSV, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Bỏ qua các dòng trống
            if row.get('short_name') and row.get('url'):
                docs_to_download.append(row)

    print(f"[*] Tổng cộng có {len(docs_to_download)} tài liệu cần tải.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50) 
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            accept_downloads=True
        )
        page = context.new_page()

        try:
            login_via_popup(page, username, password)
            download_documents(page, docs_to_download, output_dir=OUTPUT_DIR)
        finally:
            input("\nNhấn Enter để đóng trình duyệt...")
            browser.close()

if __name__ == "__main__":
    main()