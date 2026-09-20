"""
Task 1 — Download official legal PDFs for the Etomidate RAG corpus.
"""

from pathlib import Path
import re
import requests


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "landing" / "legal"


DOCUMENTS = [
    {
        "filename": "luat_73_2021_phong_chong_ma_tuy.pdf",
        "landing_page": (
            "https://chinhphu.vn/"
            "?classid=1&docid=204940&pageid=27160&typegroupid=3"
        ),
        "expected_pdf_name": "73luat.pdf",
    },
    {
        "filename": "nghi_dinh_28_2026_danh_muc_ma_tuy.pdf",
        "landing_page": (
            "https://chinhphu.vn/"
            "?classid=1&docid=216717&pageid=27160"
        ),
        "expected_pdf_name": "28-cp.signed.pdf",
    },
    {
        "filename": "nghi_dinh_163_2026_huong_dan_luat.pdf",
        "landing_page": (
            "https://chinhphu.vn/"
            "?docid=218256&pageid=27160&typegroupid=4"
        ),
        "expected_pdf_name": "163-ndcp.signed.pdf",
    },
]


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/140 Safari/537.36"
    )
}


def setup_directory() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def discover_pdf_url(landing_page: str, expected_name: str) -> str:
    """Find official datafiles.chinhphu.vn PDF attachment."""
    response = requests.get(
        landing_page,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    # Find all absolute government PDF URLs.
    urls = re.findall(
        r'https?://[^"\'<>\s]+\.pdf(?:\?[^"\'<>\s]*)?',
        response.text,
        flags=re.IGNORECASE,
    )

    # HTML may contain escaped slashes/entities.
    urls = [
        url.replace("&amp;", "&")
        .replace("\\/", "/")
        for url in urls
    ]

    # Prefer exact attachment.
    for url in urls:
        if expected_name.lower() in url.lower():
            return url

    # Otherwise accept first government datafile PDF.
    for url in urls:
        if "datafiles.chinhphu.vn" in url:
            return url

    raise RuntimeError(
        f"Cannot find PDF attachment from {landing_page}"
    )


def download_pdf(url: str, output_path: Path) -> None:
    if output_path.exists() and output_path.stat().st_size > 10_000:
        print(f"SKIP: {output_path.name}")
        return

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=60,
    )
    response.raise_for_status()

    content = response.content

    # PDF signature check
    if not content.startswith(b"%PDF"):
        raise ValueError(
            f"{url} did not return a valid PDF"
        )

    output_path.write_bytes(content)

    print(
        f"SAVED: {output_path.name} "
        f"({len(content) / 1024 / 1024:.2f} MB)"
    )


def download_documents() -> None:
    for document in DOCUMENTS:
        print("\n" + "=" * 70)
        print(document["filename"])

        pdf_url = discover_pdf_url(
            document["landing_page"],
            document["expected_pdf_name"],
        )

        print(f"PDF URL: {pdf_url}")

        download_pdf(
            pdf_url,
            DATA_DIR / document["filename"],
        )


if __name__ == "__main__":
    setup_directory()
    download_documents()