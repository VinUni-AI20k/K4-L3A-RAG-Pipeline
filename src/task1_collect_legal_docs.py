"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Chủ đề nhóm: IELTS Writing — band descriptors, tiêu chí chấm điểm, bài viết mẫu.

Nguồn: ielts.org (đồng sở hữu bởi British Council, IDP IELTS và Cambridge).
Đây là các bản public chính thức, tải trực tiếp từ CDN của ielts.org nên luôn
lấy được phiên bản mới nhất mà ban tổ chức đang phát hành.

Chạy:
    python -m src.task1_collect_legal_docs
"""

import json
from pathlib import Path

import requests


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
MANIFEST_PATH = DATA_DIR / "sources.json"

USER_AGENT = "Mozilla/5.0 (compatible; K4-Day08-RAG/0.1; academic coursework)"
REQUEST_TIMEOUT = 60

# filename -> metadata. Title giữ nguyên tên tài liệu gốc để dùng lại ở Task 3/4.
SOURCES: dict[str, dict[str, str]] = {
    "ielts-writing-band-descriptors.pdf": {
        "url": "https://ielts.org/cdn/ielts-guides/ielts-writing-band-descriptors.pdf",
        "title": "IELTS Writing Band Descriptors (public version)",
    },
    "ielts-writing-key-assessment-criteria.pdf": {
        "url": "https://ielts.org/cdn/ielts-guides/ielts-writing-key-assessment-criteria.pdf",
        "title": "IELTS Writing Key Assessment Criteria",
    },
    "ielts-academic-writing-sample-tasks.pdf": {
        "url": "https://ielts.org/cdn/Sample-tests/ielts-academic-writing-sample-tasks-2023.pdf",
        "title": "IELTS Academic Writing Sample Tasks and Sample Answers",
    },
    "ielts-general-training-writing-sample-tasks.pdf": {
        "url": "https://ielts.org/cdn/Sample-tests/ielts-general-training-writing-sample-tasks-2023.pdf",
        "title": "IELTS General Training Writing Sample Tasks and Sample Answers",
    },
    "ielts-scores-guide.pdf": {
        "url": "https://ielts.org/cdn/ielts-downloadable-assets/ielts-guidance-and-support/ielts-guides/ielts-scores-guide.pdf",
        "title": "Guide to IELTS Scores",
    },
}

MIN_BYTES = 1024


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải các PDF chính thức về data/landing/legal/ và ghi manifest nguồn."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    manifest: list[dict[str, str]] = []
    failed: list[str] = []

    for filename, meta in SOURCES.items():
        target = DATA_DIR / filename
        url = meta["url"]

        if target.exists() and target.stat().st_size > MIN_BYTES:
            print(f"Skip (đã có): {filename} ({target.stat().st_size:,} bytes)")
            manifest.append({"filename": filename, **meta})
            continue

        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as error:
            print(f"FAIL {filename}: {error}")
            failed.append(filename)
            continue

        content = response.content
        # Chặn trường hợp site trả trang lỗi HTML với status 200.
        if not content.startswith(b"%PDF") or len(content) <= MIN_BYTES:
            print(f"FAIL {filename}: nội dung không phải PDF hợp lệ")
            failed.append(filename)
            continue

        target.write_bytes(content)
        manifest.append({"filename": filename, **meta})
        print(f"OK   {filename} ({len(content):,} bytes)")

    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"\nĐã lưu {len(manifest)}/{len(SOURCES)} tài liệu vào {DATA_DIR}")
    print(f"Manifest: {MANIFEST_PATH.name}")
    if failed:
        print(f"Chưa tải được: {', '.join(failed)}")
    if len(manifest) < 3:
        raise RuntimeError("Cần tối thiểu 3 tài liệu; hãy kiểm tra lại nguồn.")


if __name__ == "__main__":
    setup_directory()
    download_documents()