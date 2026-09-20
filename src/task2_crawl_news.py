"""
Task 2 — Thu thập bài viết hướng dẫn / hỗ trợ khách hàng.

Cùng lý do với Task 1: help center của sàn TMĐT chặn crawler, nên nhóm dùng bộ
bài viết SYNTHETIC mô phỏng các câu hỏi thường gặp của người mua. Mỗi bài được
lưu thành một JSON trong data/landing/news/ với đủ metadata mà Task 3 cần.

Nếu sau này nhóm đổi sang nguồn thật, chỉ cần điền ARTICLE_URLS và bật lại
nhánh crawl trong crawl_article(); phần ghi file phía dưới giữ nguyên.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

# Để trống vì nhóm không crawl nguồn thật. Xem docstring ở trên.
ARTICLE_URLS: list[str] = []

ARTICLES = [
    {
        "url": "https://help.shopee.vn/portal/4/article/1",
        "title": "Hướng Dẫn Theo Dõi Đơn Hàng",
        "content_markdown": (
            "Để theo dõi đơn hàng của bạn trên Shopee, hãy vào mục **Tôi** > "
            "**Đơn mua** > **Đang giao**. Tại đây, bạn sẽ thấy chi tiết hành trình "
            "đơn hàng, từ lúc người bán chuẩn bị hàng, giao cho đơn vị vận chuyển, "
            "đến khi hàng được giao tới bạn. Trạng thái đơn hàng được cập nhật liên "
            "tục theo thời gian thực. Nếu quá 3 ngày trạng thái không thay đổi, bạn "
            "nên liên hệ người bán hoặc đơn vị vận chuyển để được kiểm tra lại."
        ),
    },
    {
        "url": "https://help.shopee.vn/portal/4/article/2",
        "title": "Cách Đổi Phương Thức Thanh Toán",
        "content_markdown": (
            "Bạn có thể thay đổi phương thức thanh toán trước khi người bán xác nhận "
            "đơn hàng. Vào trang **Chi tiết đơn hàng**, chọn **Đổi phương thức thanh "
            "toán** và chọn phương thức mong muốn (ví dụ: Ví ShopeePay, Thẻ tín dụng, "
            "hoặc Thanh toán khi nhận hàng). Xin lưu ý, nếu đơn hàng đã được người bán "
            "xác nhận, bạn không thể thay đổi phương thức thanh toán nữa; khi đó lựa "
            "chọn duy nhất là hủy đơn và đặt lại từ đầu."
        ),
    },
    {
        "url": "https://help.shopee.vn/portal/4/article/3",
        "title": "Bằng Chứng Cần Thiết Để Hoàn Tiền",
        "content_markdown": (
            "Khi yêu cầu hoàn tiền cho sản phẩm bị lỗi hoặc thiếu, bạn cần cung cấp "
            "**video mở hộp (unboxing video)** không cắt ghép. Video phải quay rõ mã "
            "vận đơn, toàn cảnh quá trình bóc hàng và tình trạng thực tế của sản phẩm. "
            "Hình ảnh rõ nét về lỗi sản phẩm cũng có thể được yêu cầu để hỗ trợ quá "
            "trình đối soát nhanh chóng hơn. Thiếu video mở hộp là lý do từ chối phổ "
            "biến nhất đối với các yêu cầu hoàn tiền hàng giá trị cao."
        ),
    },
    {
        "url": "https://help.shopee.vn/portal/4/article/4",
        "title": "Mua Hàng Xuyên Biên Giới Giao Nhận Bao Lâu?",
        "content_markdown": (
            "Đơn hàng từ quốc tế thường mất từ **7 đến 15 ngày làm việc** để giao đến "
            "tay bạn, tùy thuộc vào thủ tục hải quan và tình hình thời tiết. Bạn có "
            "thể theo dõi mã vận đơn quốc tế ngay trên ứng dụng Shopee. Nếu đơn hàng "
            "bị giao trễ quá thời gian dự kiến, hệ thống sẽ tự động bồi thường cho bạn "
            "một voucher hoặc Xu theo chính sách Đảm Bảo Giao Hàng mà không cần bạn "
            "phải gửi yêu cầu thủ công."
        ),
    },
    {
        "url": "https://help.shopee.vn/portal/4/article/5",
        "title": "Làm Gì Khi Không Nhận Được Hàng Nhưng Báo Đã Giao?",
        "content_markdown": (
            "Nếu ứng dụng báo **Đã giao** nhưng bạn chưa nhận được hàng, hãy khoan bấm "
            "*Đã nhận hàng*. Vui lòng liên hệ ngay với người thân, bảo vệ hoặc hàng "
            "xóm để xem có ai nhận hộ không. Nếu vẫn không thấy, bạn có thể gọi cho "
            "shipper qua số điện thoại trên hệ thống, hoặc bấm nút **Yêu cầu Trả "
            "hàng/Hoàn tiền** với lý do 'Chưa nhận được hàng' trong vòng 24 giờ kể từ "
            "khi đơn được đánh dấu đã giao thành công."
        ),
    },
]


async def crawl_article(url: str) -> dict:
    """Lấy nội dung một bài viết.

    Nhóm đang dùng corpus synthetic nên hàm này trả về bài tương ứng trong
    ARTICLES. Khi đổi sang nguồn thật, thay phần thân bằng Crawl4AI/Firecrawl
    và giữ nguyên 4 field output.
    """
    for article in ARTICLES:
        if article["url"] == url:
            return {
                "url": url,
                "title": article["title"],
                "date_crawled": datetime.now().isoformat(),
                "content_markdown": article["content_markdown"],
            }
    raise ValueError(f"Không có nội dung cho URL: {url}")


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    urls = ARTICLE_URLS or [article["url"] for article in ARTICLES]

    for index, url in enumerate(urls, 1):
        try:
            article = await crawl_article(url)
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved: {output}")
        except Exception as error:
            print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
