"""
Task 8 — PageIndex vectorless fallback.

Luồng:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu dạng PDF (landing PDF nếu có, không thì render Markdown).
    3. Cache document IDs vào data/pageindex_documents.json để không upload lại.
    4. Parse retrieved nodes thành SearchResult có retrieval_method="pageindex".

PageIndex là dịch vụ ngoài: mọi lời gọi đều có timeout và không được làm
pipeline crash. Thiếu API key hoặc lỗi mạng thì trả về danh sách rỗng.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
ROOT_DIR = Path(__file__).resolve().parent.parent
STANDARDIZED_DIR = ROOT_DIR / "data" / "standardized"
LANDING_DIR = ROOT_DIR / "data" / "landing"
DOCUMENT_CACHE = ROOT_DIR / "data" / "pageindex_documents.json"

RETRIEVAL_TIMEOUT = 60.0
POLL_INTERVAL = 2.0
UNICODE_FONT = Path("C:/Windows/Fonts/arial.ttf")

_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _client():
    """Trả PageIndexClient, hoặc None khi chưa cấu hình API key."""
    if not PAGEINDEX_API_KEY.strip():
        print("PageIndex: thiếu PAGEINDEX_API_KEY, bỏ qua fallback.")
        return None
    from pageindex import PageIndexClient

    return PageIndexClient(api_key=PAGEINDEX_API_KEY.strip())


def _load_cache() -> dict:
    if not DOCUMENT_CACHE.exists():
        return {}
    try:
        cached = json.loads(DOCUMENT_CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return cached if isinstance(cached, dict) else {}


def _save_cache(cache: dict) -> None:
    DOCUMENT_CACHE.parent.mkdir(parents=True, exist_ok=True)
    DOCUMENT_CACHE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _markdown_to_pdf(markdown_path: Path) -> Path:
    """Render Markdown sang PDF tạm vì PageIndex chỉ nhận PDF."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    text = markdown_path.read_text(encoding="utf-8")
    if UNICODE_FONT.exists():
        pdf.add_font("body", "", str(UNICODE_FONT))
        pdf.set_font("body", size=11)
    else:
        # Không có font Unicode: hạ về Helvetica và thay ký tự có dấu để không crash.
        pdf.set_font("helvetica", size=11)
        text = text.encode("latin-1", errors="replace").decode("latin-1")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.multi_cell(0, 6, text)
    output = Path(tempfile.gettempdir()) / f"{markdown_path.stem}.pdf"
    pdf.output(str(output))
    return output


def _source_pdf(markdown_path: Path) -> Path:
    """Ưu tiên PDF gốc ở landing, nếu không có thì render từ Markdown."""
    relative = markdown_path.relative_to(STANDARDIZED_DIR)
    landing_pdf = LANDING_DIR / relative.with_suffix(".pdf")
    if landing_pdf.exists():
        return landing_pdf
    return _markdown_to_pdf(markdown_path)


def upload_documents() -> None:
    """Upload tài liệu và lưu mapping source -> doc_id để tái sử dụng."""
    client = _client()
    if client is None:
        return

    cache = _load_cache()
    for markdown_path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        source = markdown_path.name
        if source in cache:
            continue
        try:
            response = client.submit_document(str(_source_pdf(markdown_path)))
            doc_id = response.get("doc_id")
        except Exception as error:  # dịch vụ ngoài: log rồi đi tiếp
            print(f"PageIndex: upload {source} thất bại ({error}).")
            continue
        if not doc_id:
            print(f"PageIndex: response cho {source} không có doc_id.")
            continue
        content = markdown_path.read_text(encoding="utf-8")
        title_match = _TITLE_RE.search(content)
        cache[source] = {
            "doc_id": doc_id,
            "title": title_match.group(1).strip() if title_match else markdown_path.stem,
            "doc_type": markdown_path.relative_to(STANDARDIZED_DIR).parts[0].lower(),
        }
        _save_cache(cache)
        print(f"PageIndex: đã upload {source} -> {doc_id}")


def _wait_for_retrieval(client, retrieval_id: str) -> list[dict]:
    """Poll retrieval cho tới khi hoàn thành hoặc hết timeout."""
    deadline = time.monotonic() + RETRIEVAL_TIMEOUT
    while time.monotonic() < deadline:
        payload = client.get_retrieval(retrieval_id)
        status = str(payload.get("status", "")).lower()
        if status in {"completed", "success", "done"}:
            retrieval = payload.get("retrieval")
            nodes = retrieval.get("nodes") if isinstance(retrieval, dict) else None
            return nodes or payload.get("nodes") or []
        if status in {"failed", "error"}:
            print(f"PageIndex: retrieval {retrieval_id} lỗi.")
            return []
        time.sleep(POLL_INTERVAL)
    print(f"PageIndex: retrieval {retrieval_id} vượt {RETRIEVAL_TIMEOUT:.0f}s, bỏ qua.")
    return []


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult, hoặc danh sách rỗng khi không dùng được."""
    if top_k <= 0 or not isinstance(query, str) or not query.strip():
        return []
    client = _client()
    if client is None:
        return []

    cache = _load_cache()
    if not cache:
        upload_documents()
        cache = _load_cache()
    if not cache:
        return []

    collected: list[tuple[float, dict]] = []
    for source, entry in cache.items():
        try:
            submitted = client.submit_query(entry["doc_id"], query.strip())
            retrieval_id = submitted.get("retrieval_id")
            if not retrieval_id:
                continue
            nodes = _wait_for_retrieval(client, retrieval_id)
        except Exception as error:
            print(f"PageIndex: query trên {source} thất bại ({error}).")
            continue

        for rank, node in enumerate(nodes, 1):
            content = str(
                node.get("text") or node.get("content") or node.get("summary") or ""
            ).strip()
            if not content:
                continue
            raw_score = node.get("relevance_score", node.get("score"))
            # API không đảm bảo có score: gán score giảm dần theo rank.
            score = float(raw_score) if isinstance(raw_score, (int, float)) else 1.0 / rank
            node_id = str(node.get("node_id") or node.get("id") or rank)
            collected.append(
                (
                    score,
                    {
                        "id": f"{source}::pageindex-{node_id}",
                        "content": content,
                        "score": score,
                        "metadata": {
                            "source": source,
                            "title": entry.get("title") or source,
                            "doc_type": entry.get("doc_type") or "legal",
                            "url": None,
                            "chunk_index": rank - 1,
                        },
                        "retrieval_method": "pageindex",
                    },
                )
            )

    collected.sort(key=lambda row: row[0], reverse=True)
    results: list[dict] = []
    seen: set[str] = set()
    for _, result in collected:
        if result["id"] in seen:
            continue
        seen.add(result["id"])
        results.append(result)
        if len(results) >= top_k:
            break
    return results


if __name__ == "__main__":
    upload_documents()
    for item in pageindex_search("chiến lược phát triển du lịch đêm", top_k=3):
        print(item["id"], round(item["score"], 4))
