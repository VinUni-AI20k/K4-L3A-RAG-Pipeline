"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
SDK pageindex không đặt timeout cho request, nên mọi lời gọi được bọc trong
thread có deadline (PAGEINDEX_TIMEOUT giây).
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
ROOT = Path(__file__).parent.parent
STANDARDIZED_DIR = ROOT / "data" / "standardized"
LEGAL_PDF_DIR = ROOT / "data" / "landing" / "legal"
PDF_CACHE_DIR = ROOT / "pageindex_pdfs"
DOC_IDS_PATH = ROOT / "pageindex_doc_ids.json"

PAGEINDEX_TIMEOUT = 20.0
POLL_INTERVAL = 1.5

_executor = ThreadPoolExecutor(max_workers=4)


class PageIndexUnavailable(RuntimeError):
    """PageIndex chưa cấu hình hoặc chưa có tài liệu đã upload."""


def _client():
    if not PAGEINDEX_API_KEY:
        raise PageIndexUnavailable("PAGEINDEX_API_KEY is not set")
    from pageindex import PageIndexClient

    return PageIndexClient(api_key=PAGEINDEX_API_KEY)


def _load_doc_ids() -> dict:
    if DOC_IDS_PATH.exists():
        return json.loads(DOC_IDS_PATH.read_text(encoding="utf-8"))
    return {}


def _pdf_for(markdown_path: Path) -> Path:
    """PDF gốc của legal; news Markdown được render tạm sang PDF."""
    from .task1_collect_legal_docs import render_markdown_to_pdf
    from .task4_chunking_indexing import parse_frontmatter

    legal_pdf = LEGAL_PDF_DIR / f"{markdown_path.stem}.pdf"
    if legal_pdf.exists():
        return legal_pdf
    front, body = parse_frontmatter(markdown_path.read_text(encoding="utf-8"))
    PDF_CACHE_DIR.mkdir(exist_ok=True)
    output = PDF_CACHE_DIR / f"{markdown_path.stem}.pdf"
    render_markdown_to_pdf(front.get("title", markdown_path.stem), front.get("url", ""), body, output)
    return output


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    from .task4_chunking_indexing import parse_frontmatter

    client = _client()
    doc_ids = _load_doc_ids()
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        key = path.relative_to(STANDARDIZED_DIR).as_posix()
        if key in doc_ids:
            print(f"Cached: {key} → {doc_ids[key]['doc_id']}")
            continue
        front, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        response = client.submit_document(str(_pdf_for(path)))
        doc_id = response.get("doc_id")
        if not doc_id:
            print(f"Upload failed: {key} — {response}")
            continue
        doc_ids[key] = {
            "doc_id": doc_id,
            "source": front.get("source_file") or path.name,
            "title": front.get("title") or path.stem,
            "doc_type": "legal" if key.startswith("legal/") else "news",
            "url": front.get("url"),
        }
        DOC_IDS_PATH.write_text(json.dumps(doc_ids, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Uploaded: {key} → {doc_id}")


def _query_document(client, doc_id: str, query: str, deadline: float) -> list[dict]:
    """Submit query và poll tới khi có retrieved nodes hoặc hết deadline."""
    retrieval_id = client.submit_query(doc_id, query)["retrieval_id"]
    while time.monotonic() < deadline:
        response = client.get_retrieval(retrieval_id)
        status = response.get("status")
        if status == "completed":
            return response.get("retrieved_nodes") or []
        if status in {"failed", "error"}:
            raise RuntimeError(f"PageIndex retrieval failed: {response}")
        time.sleep(POLL_INTERVAL)
    return []


def _node_text(node: dict) -> str:
    contents = node.get("relevant_contents") or []
    parts = [
        item.get("relevant_content", "") if isinstance(item, dict) else str(item)
        for item in contents
    ]
    return "\n".join(part for part in parts if part).strip() or str(node.get("text", "")).strip()


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult.

    Raise khi PageIndex chưa cấu hình/lỗi/timeout — Task 9 bắt lỗi và giữ
    kết quả hybrid.
    """
    client = _client()
    doc_ids = _load_doc_ids()
    if not doc_ids:
        raise PageIndexUnavailable("No uploaded documents; run python -m src.task8_pageindex_vectorless")

    deadline = time.monotonic() + PAGEINDEX_TIMEOUT
    futures = {
        key: _executor.submit(_query_document, client, info["doc_id"], query, deadline)
        for key, info in doc_ids.items()
    }
    candidates = []
    for key, future in futures.items():
        try:
            nodes = future.result(timeout=max(0.0, deadline - time.monotonic()) + 1)
        except Exception:  # timeout hoặc lỗi của một tài liệu: bỏ qua tài liệu đó
            continue
        info = doc_ids[key]
        for rank, node in enumerate(nodes):
            text = _node_text(node)
            if not text:
                continue
            node_id = str(node.get("node_id") or rank)
            candidates.append({
                "id": f"pageindex::{key}::{node_id}",
                "content": text,
                "rank": rank,
                "metadata": {
                    "source": info["source"],
                    "title": info["title"],
                    "doc_type": info["doc_type"],
                    "url": info.get("url"),
                    "chunk_index": rank,
                    "node_title": str(node.get("title", "")),
                },
            })

    # API không trả score: xếp theo rank trong từng tài liệu, score = 1 / (1 + rank).
    candidates.sort(key=lambda item: item["rank"])
    results, seen = [], set()
    for item in candidates:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        rank = item.pop("rank")
        results.append({**item, "score": 1.0 / (1 + rank), "retrieval_method": "pageindex"})
        if len(results) >= top_k:
            break
    return results


if __name__ == "__main__":
    upload_documents()
