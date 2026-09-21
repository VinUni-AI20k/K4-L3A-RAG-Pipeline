"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ (PDF).
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
Thiếu API key thì trả về danh sách rỗng — pipeline tự dùng hybrid results.
"""

import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import sleep

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CACHE_FILE = Path(__file__).parent.parent / ".pageindex_cache.json"

REQUEST_TIMEOUT_SECONDS = 30
POLL_INTERVAL_SECONDS = 2
POLL_MAX_ATTEMPTS = 30

_FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/times.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/Library/Fonts/Arial.ttf"),
]


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _get_client():
    from pageindex import PageIndexClient

    return PageIndexClient(PAGEINDEX_API_KEY)


def _with_timeout(func, args=(), timeout: int = REQUEST_TIMEOUT_SECONDS):
    """Chạy blocking HTTP call trong thread có timeout (SDK không nhận timeout)."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args)
        return future.result(timeout=timeout)


def _parse_metadata(md_path: Path) -> dict:
    """Rút metadata từ Markdown chuẩn hoá: title, url, doc_type."""
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    title = md_path.stem
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    url = None
    for line in text.splitlines():
        if line.startswith("**Source:**"):
            url = line.replace("**Source:**", "").strip() or None
            break
    doc_type = "legal" if "legal" in md_path.parts else "news"
    return {
        "source": md_path.name,
        "title": title,
        "doc_type": doc_type,
        "url": url,
    }


def _hard_wrap(line: str, width: int = 150) -> list[str]:
    """Cắt nhỏ token quá dài (URL, mã số OCR) để multi_cell không bị kẹt."""
    if len(line) <= width:
        return [line]
    return [line[start : start + width] for start in range(0, len(line), width)]


def _md_to_pdf(md_path: Path) -> Path:
    """Convert Markdown sang PDF tạm; cần font Unicode cho tiếng Việt."""
    from fpdf import FPDF

    font_path = next((path for path in _FONT_CANDIDATES if path.exists()), None)
    if font_path is None:
        raise ValueError(f"No Unicode font found for PDF conversion of {md_path.name}")

    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("unicode", "", str(font_path))
    pdf.set_font("unicode", size=11)
    for line in md_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        for piece in _hard_wrap(line):
            # new_x/new_y để x reset về lề trái sau mỗi cell; mặc định để x
            # ở mép phải làm multi_cell sau đó không còn chỗ ngang.
            pdf.multi_cell(0, 6, piece, new_x="LMARGIN", new_y="NEXT")
    output = Path(tempfile.gettempdir()) / f"{md_path.stem}.pdf"
    pdf.output(str(output))
    return output


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    if not PAGEINDEX_API_KEY:
        print("Skipped: PAGEINDEX_API_KEY is empty — fallback stays disabled.")
        return

    client = _get_client()
    cache = _load_cache()
    for md_path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        key = md_path.relative_to(STANDARDIZED_DIR).as_posix()
        if key in cache:
            print(f"Skipped (already uploaded): {key}")
            continue
        try:
            pdf_path = _md_to_pdf(md_path)
            response = _with_timeout(client.submit_document, (str(pdf_path),))
            cache[key] = {**_parse_metadata(md_path), "doc_id": response["doc_id"]}
            _save_cache(cache)
            print(f"Uploaded: {key} -> {response['doc_id']}")
        except Exception as exc:
            print(f"Failed: {key} — {exc}")


def _extract_nodes(retrieval_response: dict) -> list[dict]:
    """Lấy list node từ response — không đoán cứng một tên field duy nhất."""
    if not isinstance(retrieval_response, dict):
        return []
    data = retrieval_response.get("retrieval", retrieval_response)
    if isinstance(data, dict):
        for key in ("results", "references", "chunks", "nodes", "content"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _node_score(node: dict, rank: int) -> float:
    """Dùng score của API nếu có; không thì gán giảm dần theo rank."""
    for key in ("score", "similarity", "relevance"):
        value = node.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return 1.0 / (rank + 1)


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if not PAGEINDEX_API_KEY or top_k <= 0:
        return []
    cache = _load_cache()
    if not cache:
        return []

    client = _get_client()
    results = []
    for entry in cache.values():
        doc_id = entry["doc_id"]
        try:
            submitted = _with_timeout(client.submit_query, (doc_id, query))
            retrieval_id = submitted["retrieval_id"]

            response = None
            for _ in range(POLL_MAX_ATTEMPTS):
                response = _with_timeout(client.get_retrieval, (retrieval_id,))
                if not isinstance(response, dict) or response.get(
                    "status"
                ) not in {"pending", "processing", "running"}:
                    break
                sleep(POLL_INTERVAL_SECONDS)

            for rank, node in enumerate(_extract_nodes(response)[:top_k], 1):
                content = node.get("content") or node.get("text") or node.get("markdown")
                if not isinstance(content, str) or not content.strip():
                    continue
                results.append(
                    {
                        "id": f"{doc_id}::node-{rank}",
                        "content": content,
                        "score": _node_score(node, rank),
                        "metadata": {
                            "source": entry["source"],
                            "title": entry["title"],
                            "doc_type": entry["doc_type"],
                            "url": entry.get("url"),
                            "chunk_index": rank - 1,
                        },
                        "retrieval_method": "pageindex",
                    }
                )
        except Exception as exc:
            print(f"PageIndex retrieval failed for {doc_id}: {exc}")

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    upload_documents()
