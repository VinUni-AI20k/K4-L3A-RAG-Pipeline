"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Chủ đề nhóm: hỗ trợ khách hàng trên sàn thương mại điện tử (Shopee).

Lưu ý về nguồn dữ liệu:
    Trung tâm trợ giúp và trang chính sách của các sàn TMĐT Việt Nam đều đứng
    sau WAF/Captcha và cấm crawler trong robots.txt. Vì bài lab không cho phép
    vượt WAF, nhóm dựng bộ corpus SYNTHETIC mô phỏng lại đúng cấu trúc và văn
    phong của tài liệu chính sách thật, rồi xuất ra PDF bằng fpdf2.

    Toàn bộ nội dung trong file này là dữ liệu tự soạn, KHÔNG phải trích dẫn
    nguyên văn từ Shopee. Mọi báo cáo dùng corpus này phải ghi rõ điều đó.
"""

from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

# Font Unicode để render được tiếng Việt có dấu; fpdf2 core font chỉ có latin-1.
FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
)

DOCUMENTS = [
    {
        "filename": "returns-refund-policy-shopee.pdf",
        "title": "Chính Sách Trả Hàng và Hoàn Tiền",
        "content": (
            "Người mua có thể yêu cầu trả hàng/hoàn tiền trong vòng 15 ngày kể từ ngày "
            "nhận hàng đối với sản phẩm thuộc Shopee Mall, và 3 ngày đối với sản phẩm "
            "thường. Các trường hợp được chấp nhận bao gồm: hàng bị lỗi, giao sai sản "
            "phẩm, hoặc hàng giả/nhái. Người mua cần cung cấp video mở hộp và hình ảnh "
            "rõ nét làm bằng chứng. Trong trường hợp người bán từ chối yêu cầu, Shopee "
            "sẽ đứng ra giải quyết tranh chấp dựa trên bằng chứng của cả hai bên."
        ),
    },
    {
        "filename": "payment-methods-shopee.pdf",
        "title": "Phương Thức Thanh Toán Hợp Lệ",
        "content": (
            "Shopee hỗ trợ nhiều phương thức thanh toán nhằm mang lại sự tiện lợi cho "
            "người dùng. Khách hàng có thể thanh toán bằng: 1. Thẻ Tín dụng/Ghi nợ "
            "(Visa, Mastercard, JCB). 2. Ví ShopeePay (ưu tiên với nhiều voucher giảm "
            "giá). 3. Thanh toán khi nhận hàng (COD). 4. Trả góp qua thẻ tín dụng hoặc "
            "SPayLater. Mọi giao dịch qua thẻ đều được mã hóa và bảo mật theo tiêu "
            "chuẩn quốc tế. Shopee không hỗ trợ thanh toán qua chuyển khoản ngân hàng "
            "trực tiếp cho người bán."
        ),
    },
    {
        "filename": "product-listing-regulations-shopee.pdf",
        "title": "Quy Định Đăng Bán Sản Phẩm Cho Người Bán",
        "content": (
            "Người bán trên Shopee phải tuân thủ nghiêm ngặt các quy định về đăng bán "
            "sản phẩm. Cụ thể: 1. Không đăng bán hàng giả, hàng nhái, hàng vi phạm bản "
            "quyền. 2. Hình ảnh sản phẩm phải rõ nét, không chứa thông tin liên hệ bên "
            "ngoài hoặc logo của sàn TMĐT khác. 3. Mô tả sản phẩm phải chính xác, không "
            "dùng từ ngữ gây hiểu lầm hoặc vi phạm thuần phong mỹ tục. Người bán vi "
            "phạm sẽ bị khóa tài khoản hoặc xóa sản phẩm mà không cần báo trước."
        ),
    },
]


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def find_unicode_font() -> Path:
    """Tìm một TTF có sẵn trên máy để render tiếng Việt."""
    for candidate in FONT_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Không tìm thấy font Unicode (.ttf) để render tiếng Việt. "
        f"Đã thử: {', '.join(str(path) for path in FONT_CANDIDATES)}. "
        "Hãy thêm đường dẫn font của máy bạn vào FONT_CANDIDATES."
    )


def create_policy_pdf(filename: str, title: str, content: str) -> Path:
    """Render một tài liệu chính sách ra PDF."""
    from fpdf import FPDF

    font_path = find_unicode_font()
    filepath = DATA_DIR / filename

    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("body", "", str(font_path))

    pdf.set_font("body", size=14)
    pdf.multi_cell(0, 10, title, align="C")
    pdf.ln(6)

    pdf.set_font("body", size=12)
    pdf.multi_cell(0, 8, content)
    pdf.ln(6)

    pdf.set_font("body", size=9)
    pdf.multi_cell(
        0,
        6,
        "Ghi chú: tài liệu synthetic do nhóm tự soạn phục vụ bài lab RAG, "
        "không phải văn bản chính thức của Shopee.",
    )

    pdf.output(str(filepath))
    print(f"Saved: {filepath} ({filepath.stat().st_size} bytes)")
    return filepath


def download_documents() -> None:
    """Sinh đủ 3 tài liệu chính sách vào data/landing/legal/."""
    for document in DOCUMENTS:
        create_policy_pdf(
            document["filename"], document["title"], document["content"]
        )


if __name__ == "__main__":
    setup_directory()
    download_documents()
