"""
Task 1 — Thu thập tài liệu pháp luật bất động sản.

Chủ đề: Pháp luật cho hộ kinh doanh / bất động sản
Tài liệu đã thu thập (lưu tại data/landing/legal/):
    1. bo-luat-dan-su.pdf       — Bộ luật Dân sự 2015
    2. luat-kinh-doanh-bds.pdf  — Luật Kinh doanh Bất động sản 2023
    3. luat-nha-o.pdf           — Luật Nhà ở 2023
    4. mau-so-1a.docx           — Mẫu hợp đồng mua bán nhà ở

Các tài liệu được tải thủ công từ nguồn công khai:
    - https://thuvienphapluat.vn
    - https://vanban.chinhphu.vn
"""

from pathlib import Path
from src.contracts import Document


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

# Metadata cho từng tài liệu đã thu thập
LEGAL_DOCUMENTS_METADATA = [
    {
        "filename": "bo-luat-dan-su.pdf",
        "title": "Bộ luật Dân sự 2015",
        "source": "bo-luat-dan-su.pdf",
        "doc_type": "legal",
        "url": "https://thuvienphapluat.vn/van-ban/Quyen-dan-su/Bo-luat-dan-su-2015-296215.aspx",
    },
    {
        "filename": "luat-kinh-doanh-bds.pdf",
        "title": "Luật Kinh doanh Bất động sản 2023",
        "source": "luat-kinh-doanh-bds.pdf",
        "doc_type": "legal",
        "url": "https://thuvienphapluat.vn/van-ban/Kinh-doanh-bat-dong-san/Luat-kinh-doanh-bat-dong-san-2023-580644.aspx",
    },
    {
        "filename": "luat-nha-o.pdf",
        "title": "Luật Nhà ở 2023",
        "source": "luat-nha-o.pdf",
        "doc_type": "legal",
        "url": "https://thuvienphapluat.vn/van-ban/Xay-dung-Do-thi/Luat-Nha-o-2023-580643.aspx",
    },
    {
        "filename": "mau-so-1a.docx",
        "title": "Mẫu số 1a — Hợp đồng mua bán nhà ở",
        "source": "mau-so-1a.docx",
        "doc_type": "legal",
        "url": None,
    },
]


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Kiểm tra và liệt kê các tài liệu đã thu thập thủ công.

    Các tài liệu pháp luật được tải thủ công từ nguồn công khai do
    các trang web có cơ chế bảo vệ (captcha / WAF).
    """
    setup_directory()

    missing = []
    for meta in LEGAL_DOCUMENTS_METADATA:
        path = DATA_DIR / meta["filename"]
        if path.exists() and path.stat().st_size > 1024:
            print(f"  [OK] {meta['filename']} ({path.stat().st_size:,} bytes)")
        else:
            missing.append(meta["filename"])
            print(f"  [MISSING] {meta['filename']}")

    if missing:
        print(f"\nCảnh báo: {len(missing)} file chưa có. Tải thủ công vào {DATA_DIR}")
        print("Nguồn: https://thuvienphapluat.vn | https://vanban.chinhphu.vn")
    else:
        print(f"\nĐã có đủ {len(LEGAL_DOCUMENTS_METADATA)} tài liệu.")


def collect_legal_documents() -> list[Document]:
    """Trả về danh sách Document từ các file đã có trong data/landing/legal/.

    Returns:
        list[Document]: Danh sách tài liệu theo contract, chỉ bao gồm
        các file thực sự tồn tại và có kích thước > 1 KB.
    """
    documents: list[Document] = []

    for meta in LEGAL_DOCUMENTS_METADATA:
        path = DATA_DIR / meta["filename"]
        if not path.exists() or path.stat().st_size <= 1024:
            print(f"  [SKIP] {meta['filename']} — không tìm thấy hoặc file rỗng")
            continue

        doc: Document = {
            "id": path.stem,  # tên file không có extension, ví dụ: "bo-luat-dan-su"
            "content": f"[Binary file: {meta['filename']}]",  # nội dung sẽ được xử lý ở Task 3
            "metadata": {
                "source": meta["source"],
                "title": meta["title"],
                "doc_type": meta["doc_type"],
                "url": meta["url"],
            },
        }
        documents.append(doc)
        print(f"  [LOADED] {meta['filename']} — {meta['title']}")

    print(f"\nTổng: {len(documents)} tài liệu pháp luật.")
    return documents


if __name__ == "__main__":
    download_documents()
    print()
    docs = collect_legal_documents()
    for doc in docs:
        print(f"  id={doc['id']} | title={doc['metadata']['title']}")
