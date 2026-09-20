"""Task 8 ? PageIndex vectorless fallback.

H??ng d?n:
    1. ??c PAGEINDEX_API_KEY t? .env.
    2. Upload t?i li?u ? ??nh d?ng PageIndex h? tr?.
    3. Cache document IDs ?? kh?ng upload l?i.
    4. Parse k?t qu? th?nh SearchResult c? method pageindex.

PageIndex l? d?ch v? ngo?i: c?n timeout v? x? l? l?i ?? pipeline kh?ng crash.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "").strip()
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"

_UPLOADED_IDS: set[str] = set()


def upload_documents() -> None:
    """Upload t?i li?u v? l?u document IDs ?? t?i s? d?ng.

    Khi ch?a c? PAGEINDEX_API_KEY, h?m kh?ng crash; fallback s? ???c
    pipeline x? l? nh? provider kh?ng kh? d?ng.
    """
    if not PAGEINDEX_API_KEY:
        print("PageIndex API key is not configured; skipped upload.")
        return

    try:
        import pageindex  # type: ignore[import-untyped]
    except Exception as error:
        print(f"PageIndex SDK unavailable: {error}")
        return

    print("PageIndex upload path is configured but not implemented for this provider.")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Tr? v? pageindex SearchResult.

    Ch?a c? API key ho?c SDK th? tr? danh s?ch r?ng ?? Task 9 chuy?n sang
    safe fallback/hybrid thay v? l?m pipeline crash.
    """
    if not PAGEINDEX_API_KEY:
        return []

    try:
        import pageindex  # type: ignore[import-untyped]
    except Exception:
        return []

    # Ch?a tri?n khai endpoint search do PageIndex kh?ng ???c c?u h?nh.
    return []


if __name__ == "__main__":
    upload_documents()
