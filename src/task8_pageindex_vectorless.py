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
import logging
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .contracts import SearchResult, validate_search_results


load_dotenv()

logger = logging.getLogger(__name__)

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
PAGEINDEX_TIMEOUT = int(os.getenv("PAGEINDEX_TIMEOUT", "30"))

ROOT_DIR = Path(__file__).parent.parent
STANDARDIZED_DIR = ROOT_DIR / "data" / "standardized"
LEGAL_LANDING_DIR = ROOT_DIR / "data" / "landing" / "legal"
CACHE_FILE = ROOT_DIR / "pageindex_doc_ids.json"
TEMP_PDF_DIR = ROOT_DIR / "data" / "_tmp_pdf"


def load_cache() -> dict[str, dict]:
    """Đọc mapping document ID từ file cache JSON."""
    if not CACHE_FILE.exists():
        return {}
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception as exc:
        logger.warning("Không thể đọc cache PageIndex: %s", exc)
    return {}


def save_cache(cache: dict[str, dict]) -> None:
    """Lưu mapping document ID vào file cache JSON."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def convert_markdown_to_pdf(md_path: Path, output_pdf_path: Path) -> Path:
    """Convert tài liệu Markdown sang PDF tạm thời để upload lên PageIndex."""
    from fpdf import FPDF

    content = md_path.read_text(encoding="utf-8")
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = FPDF()
    pdf.add_page()

    # Tìm font Unicode hệ thống để hiển thị đúng tiếng Việt
    font_candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    font_loaded = False
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                pdf.add_font("SysUnicode", "", font_path)
                pdf.set_font("SysUnicode", size=11)
                font_loaded = True
                break
            except Exception:
                continue

    if not font_loaded:
        pdf.set_font("Helvetica", size=11)
        content = content.encode("latin-1", "replace").decode("latin-1")

    for line in content.splitlines():
        if not line.strip():
            pdf.ln(5)
            continue
        pdf.multi_cell(0, 7, line)

    pdf.output(str(output_pdf_path))
    return output_pdf_path


def upload_documents(docs_dir: Path | None = None) -> dict[str, dict]:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    if not PAGEINDEX_API_KEY:
        raise ValueError("PAGEINDEX_API_KEY chưa được cấu hình trong .env")

    from pageindex import PageIndexClient

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
    cache = load_cache()

    search_dir = docs_dir or STANDARDIZED_DIR
    target_files: list[Path] = []
    if search_dir.exists():
        target_files = [
            p for p in search_dir.rglob("*.md")
            if p.is_file() and not p.name.startswith(".")
        ]

    # Nếu chưa có file standardized markdown, thử tìm PDF từ data/landing/legal
    if not target_files and LEGAL_LANDING_DIR.exists():
        target_files = [
            p for p in LEGAL_LANDING_DIR.glob("*.pdf")
            if p.is_file() and not p.name.startswith(".")
        ]

    if not target_files:
        logger.info("Không tìm thấy tài liệu để upload trong %s", search_dir)
        return cache

    TEMP_PDF_DIR.mkdir(parents=True, exist_ok=True)

    for path in target_files:
        doc_key = path.name
        # 3. Cache document IDs để không upload lại
        if doc_key in cache and cache[doc_key].get("doc_id"):
            logger.info("Đã có trong cache: %s -> doc_id=%s", doc_key, cache[doc_key]["doc_id"])
            continue

        # Chuẩn bị file upload dạng PDF
        if path.suffix.lower() == ".pdf":
            upload_path = path
        else:
            temp_pdf = TEMP_PDF_DIR / f"{path.stem}.pdf"
            upload_path = convert_markdown_to_pdf(path, temp_pdf)

        logger.info("Đang upload %s lên PageIndex...", path.name)
        res = client.submit_document(str(upload_path))
        doc_id = res.get("doc_id") if isinstance(res, dict) else None
        if not doc_id:
            raise RuntimeError(f"Upload thất bại cho {path.name}: {res}")

        doc_type = "legal" if "legal" in path.parts else "news"
        cache[doc_key] = {
            "doc_id": doc_id,
            "source": path.name,
            "title": path.stem,
            "doc_type": doc_type,
            "url": None,
        }
        save_cache(cache)
        logger.info("Upload thành công: %s -> %s", path.name, doc_id)

    return cache


def parse_pageindex_response(
    retrieval_data: dict[str, Any],
    doc_info: dict[str, Any],
) -> list[dict]:
    """Parse retrieved nodes từ PageIndex thành danh sách SearchResult."""
    results: list[dict] = []
    source = str(doc_info.get("source") or "pageindex_doc")
    title = str(doc_info.get("title") or "PageIndex Document")
    doc_type = str(doc_info.get("doc_type") or "legal")
    url = doc_info.get("url")

    nodes = retrieval_data.get("retrieved_nodes")
    if not isinstance(nodes, list):
        nodes = retrieval_data.get("results")
    if not isinstance(nodes, list):
        nodes = []

    # Fallback nếu API trả text trực tiếp
    if not nodes and "extracted_text" in retrieval_data:
        text = str(retrieval_data["extracted_text"]).strip()
        if text:
            results.append({
                "id": f"{source}::pageindex-0",
                "content": text,
                "score": 1.0,
                "metadata": {
                    "source": source,
                    "title": title,
                    "doc_type": doc_type,
                    "url": url,
                    "chunk_index": 0,
                },
                "retrieval_method": "pageindex",
            })
            return results

    for rank, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue

        node_score = node.get("score")
        relevant_contents = node.get("relevant_contents")

        if isinstance(relevant_contents, list) and relevant_contents:
            for sub_idx, item in enumerate(relevant_contents):
                if not isinstance(item, dict):
                    continue
                text = item.get("relevant_content") or item.get("content") or ""
                text = str(text).strip()
                if not text:
                    continue

                p_idx = item.get("page_index")
                chunk_index = p_idx if isinstance(p_idx, int) and p_idx >= 0 else rank
                score = item.get("score", node_score)
                if not isinstance(score, (int, float)) or isinstance(score, bool):
                    score = round(1.0 / (1 + len(results)), 4)

                results.append({
                    "id": f"{source}::node-{rank}-{sub_idx}",
                    "content": text,
                    "score": float(score),
                    "metadata": {
                        "source": source,
                        "title": str(node.get("title") or title),
                        "doc_type": doc_type,
                        "url": url,
                        "chunk_index": chunk_index,
                    },
                    "retrieval_method": "pageindex",
                })
        else:
            text = (
                node.get("content")
                or node.get("text")
                or node.get("relevant_content")
                or node.get("summary")
                or node.get("title")
                or ""
            )
            text = str(text).strip()
            if not text:
                continue

            p_idx = node.get("page_index")
            chunk_index = p_idx if isinstance(p_idx, int) and p_idx >= 0 else rank
            score = node_score
            if not isinstance(score, (int, float)) or isinstance(score, bool):
                score = round(1.0 / (1 + len(results)), 4)

            results.append({
                "id": f"{source}::node-{rank}",
                "content": text,
                "score": float(score),
                "metadata": {
                    "source": source,
                    "title": str(node.get("title") or title),
                    "doc_type": doc_type,
                    "url": url,
                    "chunk_index": chunk_index,
                },
                "retrieval_method": "pageindex",
            })

    return results


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult với timeout và parsing chuẩn contract."""
    if not PAGEINDEX_API_KEY:
        logger.warning("PAGEINDEX_API_KEY chưa được thiết lập.")
        return []

    cache = load_cache()
    if not cache:
        logger.warning("Chưa có document ID nào được cache trong %s", CACHE_FILE)
        return []

    from pageindex import PageIndexClient

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
    all_results: list[dict] = []

    for doc_key, doc_info in cache.items():
        doc_id = doc_info.get("doc_id")
        if not doc_id:
            continue

        # Gửi query retrieval
        submit_res = client.submit_query(doc_id=doc_id, query=query)
        retrieval_id = submit_res.get("retrieval_id") if isinstance(submit_res, dict) else None
        if not retrieval_id:
            logger.warning("Không nhận được retrieval_id cho doc_id %s", doc_id)
            continue

        # Polling kết quả có timeout
        start_time = time.time()
        completed_data = None
        while time.time() - start_time < PAGEINDEX_TIMEOUT:
            status_res = client.get_retrieval(retrieval_id)
            status = status_res.get("status") if isinstance(status_res, dict) else None
            if status == "completed":
                completed_data = status_res
                break
            elif status in ("failed", "error"):
                raise RuntimeError(f"PageIndex retrieval {retrieval_id} thất bại: {status_res}")
            time.sleep(1.0)

        if completed_data is None:
            raise TimeoutError(
                f"PageIndex retrieval {retrieval_id} vượt quá timeout {PAGEINDEX_TIMEOUT}s"
            )

        parsed_items = parse_pageindex_response(completed_data, doc_info)
        all_results.extend(parsed_items)

    # Khử trùng ID
    seen_ids: set[str] = set()
    unique_results: list[dict] = []
    for item in all_results:
        if item["id"] not in seen_ids:
            seen_ids.add(item["id"])
            unique_results.append(item)

    # Đảm bảo score giảm dần theo thứ hạng
    unique_results.sort(key=lambda x: x["score"], reverse=True)
    for rank, item in enumerate(unique_results):
        # Nếu score không strictly decreasing hoặc bằng nhau, chuẩn hóa để đảm bảo sort descending
        if rank > 0 and item["score"] > unique_results[rank - 1]["score"]:
            item["score"] = unique_results[rank - 1]["score"]

    final_results = unique_results[:top_k]
    if final_results:
        validate_search_results(final_results, top_k=top_k, expected_method="pageindex")

    return final_results


if __name__ == "__main__":
    upload_documents()
