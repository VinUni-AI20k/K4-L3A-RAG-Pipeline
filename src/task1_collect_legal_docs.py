"""Download the official policy corpus for 2026 university admissions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import requests


ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "landing" / "legal"
MANIFEST_PATH = ROOT / "data" / "legal_sources.json"

# Government Gazette copies are used for the two national circulars. The third
# document is VNU's official institution-level admissions regulation.
LEGAL_DOCUMENTS = [
    {
        "filename": "thong_tu_06_2026_quy_che_tuyen_sinh.pdf",
        "title": (
            "Thông tư 06/2026/TT-BGDĐT ban hành Quy chế tuyển sinh các ngành "
            "đào tạo trình độ đại học và ngành Giáo dục Mầm non trình độ cao đẳng"
        ),
        "document_number": "06/2026/TT-BGDĐT",
        "issued_date": "2026-02-15",
        "publisher": "Bộ Giáo dục và Đào tạo",
        "url": (
            "https://congbaocdn.chinhphu.vn/180507251028987904/2026/3/13/"
            "469029-1773305184_v1_1773394437_signed.pdf"
        ),
        "landing_page": (
            "https://congbao.chinhphu.vn/van-ban/"
            "thong-tu-so-06-2026-tt-bgddt-469029.htm"
        ),
    },
    {
        "filename": "thong_tu_34_2026_xac_dinh_so_luong_tuyen_sinh.pdf",
        "title": (
            "Thông tư 34/2026/TT-BGDĐT quy định việc xác định số lượng tuyển sinh"
        ),
        "document_number": "34/2026/TT-BGDĐT",
        "issued_date": "2026-04-19",
        "publisher": "Bộ Giáo dục và Đào tạo",
        "url": (
            "https://congbaocdn.chinhphu.vn/180507251028987904/2026/5/8/"
            "469435-1778117920_v1_1778225748_signed.pdf"
        ),
        "landing_page": (
            "https://congbao.chinhphu.vn/van-ban/"
            "thong-tu-so-34-2026-tt-bgddt-469435.htm"
        ),
    },
    {
        "filename": "quyet_dinh_955_2026_quy_che_tuyen_sinh_dhqghn.pdf",
        "title": (
            "Quyết định 955/QĐ-ĐHQGHN ban hành Quy chế tuyển sinh đại học "
            "tại Đại học Quốc gia Hà Nội"
        ),
        "document_number": "955/QĐ-ĐHQGHN",
        "issued_date": "2026-03-20",
        "publisher": "Đại học Quốc gia Hà Nội",
        "url": (
            "https://cdnportal.vnu.edu.vn/data/0/documents/2026/03/20/"
            "upload_2/955-qd-dhqghn-2026.pdf"
        ),
        "landing_page": (
            "https://vnu.edu.vn/ban-hanh-quy-che-tuyen-sinh-dai-hoc-tai-"
            "dai-hoc-quoc-gia-ha-noi-doc2759.html"
        ),
    },
]


def setup_directory() -> None:
    """Create the landing directory for original legal documents."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def _download_pdf(url: str, destination: Path) -> None:
    response = requests.get(
        url,
        timeout=90,
        headers={"User-Agent": "K4-RAG-coursework-corpus/1.0"},
    )
    response.raise_for_status()
    if not response.content.startswith(b"%PDF-"):
        raise ValueError(f"Expected PDF content from {url}")
    if len(response.content) <= 1024:
        raise ValueError(f"Downloaded PDF is unexpectedly small: {url}")
    destination.write_bytes(response.content)


def download_documents() -> None:
    """Download all official PDFs and write a provenance manifest."""
    setup_directory()
    manifest = []
    for source in LEGAL_DOCUMENTS:
        destination = DATA_DIR / source["filename"]
        _download_pdf(source["url"], destination)
        item = {
            **source,
            "bytes": destination.stat().st_size,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        }
        manifest.append(item)
        print(f"Saved: {destination}")

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved: {MANIFEST_PATH}")


if __name__ == "__main__":
    download_documents()
