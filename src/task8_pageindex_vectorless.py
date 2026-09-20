"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CACHE_FILE = Path(__file__).parent.parent / "data" / "pageindex_cache.json"


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    if not PAGEINDEX_API_KEY:
        print("PAGEINDEX_API_KEY không được thiết lập. Bỏ qua upload PageIndex.")
        return

    try:
        # Nếu có client PageIndex
        pass
    except Exception as error:
        print(f"Lỗi khi upload tài liệu lên PageIndex: {error}")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if not PAGEINDEX_API_KEY:
        return []

    try:
        # Gọi tìm kiếm qua PageIndex API hoặc SDK
        # Parse kết quả thành list[SearchResult] với retrieval_method="pageindex"
        return []
    except Exception as error:
        # Xử lý lỗi an toàn để pipeline không crash
        print(f"PageIndex search error: {error}")
        return []


if __name__ == "__main__":
    upload_documents()
    print("PageIndex module ready.")
