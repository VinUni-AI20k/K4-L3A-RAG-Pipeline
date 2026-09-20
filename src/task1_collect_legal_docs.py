"""Task 1 - Collect at least 3 public policy PDF/DOCX files.

The originals stay in data/landing/legal/ so Task 3 can re-import them.
The corpus is prompt-injection / secure AI policy material.
"""

from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

SOURCES = {
    "NIST_AI_600-1_GenAI_Profile.pdf": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf",
    "NIST_AI_100-4_Prompt_Engineering.pdf": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-4.pdf",
    "Prompt_Injection_Formalization_Benchmarking.pdf": "https://arxiv.org/pdf/2302.12173",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/125 Safari/537.36"
    )
}


def setup_directory() -> None:
    """Create the landing directory for source files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Download every configured source into the landing directory."""
    setup_directory()

    for filename, url in SOURCES.items():
        destination = DATA_DIR / filename
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=60,
                allow_redirects=True,
            )
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()
            if "application/pdf" not in content_type:
                raise ValueError(f"unexpected content type: {content_type}")

            destination.write_bytes(response.content)
            if destination.stat().st_size <= 1024:
                raise ValueError("downloaded file is too small")

            print(f"Saved: {destination.name} ({destination.stat().st_size} bytes)")
        except Exception as error:
            print(f"Failed: {url} - {error}")


if __name__ == "__main__":
    download_documents()
