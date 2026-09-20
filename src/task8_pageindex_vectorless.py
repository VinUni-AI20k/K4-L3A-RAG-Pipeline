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
import time
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CACHE_FILE = Path(__file__).parent.parent / "data" / "pageindex_cache.json"


def _get_client():
    """Khởi tạo PageIndex client với API key."""
    if not PAGEINDEX_API_KEY:
        raise RuntimeError("PAGEINDEX_API_KEY is not set")
    from pageindex import PageIndexClient
    return PageIndexClient(api_key=PAGEINDEX_API_KEY)


def _load_cache() -> dict[str, str]:
    """Đọc mapping source -> doc_id từ cache file."""
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict[str, str]) -> None:
    """Lưu mapping source -> doc_id vào cache file."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def _md_to_pdf(md_path: Path) -> Path:
    """Convert Markdown sang PDF tạm để upload lên PageIndex (chỉ hỗ trợ PDF)."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Sử dụng font hỗ trợ Unicode (nếu có), fallback sang Helvetica
    font_path = Path(__file__).parent.parent / "data" / "fonts" / "DejaVuSans.ttf"
    if font_path.exists():
        pdf.add_font("DejaVu", "", str(font_path), uni=True)
        pdf.set_font("DejaVu", size=10)
    else:
        pdf.set_font("Helvetica", size=10)

    content = md_path.read_text(encoding="utf-8")
    # fpdf2 multi_cell xử lý text wrapping tự động
    pdf.multi_cell(0, 6, content)

    pdf_path = md_path.with_suffix(".pdf")
    pdf.output(str(pdf_path))
    return pdf_path


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    client = _get_client()
    cache = _load_cache()

    md_files = list(STANDARDIZED_DIR.rglob("*.md"))
    uploaded_count = 0

    for md_path in md_files:
        source_key = md_path.relative_to(STANDARDIZED_DIR).as_posix()
        if source_key in cache:
            print(f"  [cached] {source_key} -> {cache[source_key]}")
            continue

        # Convert MD -> PDF rồi upload
        pdf_path = _md_to_pdf(md_path)
        try:
            result = client.submit_document(str(pdf_path))
            doc_id = result["doc_id"]
            cache[source_key] = doc_id
            _save_cache(cache)
            uploaded_count += 1
            print(f"  [upload] {source_key} -> {doc_id}")
        finally:
            # Xóa file PDF tạm
            if pdf_path.exists():
                pdf_path.unlink()

    # Đợi tất cả documents sẵn sàng cho retrieval
    print("Waiting for documents to be ready...")
    for source_key, doc_id in cache.items():
        for _ in range(60):  # Timeout 5 phút (60 * 5s)
            try:
                if client.is_retrieval_ready(doc_id):
                    print(f"  [ready] {source_key}")
                    break
            except Exception:
                pass
            time.sleep(5)
        else:
            print(f"  [timeout] {source_key} - may not be ready yet")

    print(f"Upload complete: {uploaded_count} new, {len(cache)} total documents.")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    client = _get_client()
    cache = _load_cache()

    if not cache:
        return []

    all_results: list[dict] = []

    # Query từng document đã upload
    for source_key, doc_id in cache.items():
        try:
            # Submit query
            response = client.submit_query(doc_id=doc_id, query=query)
            retrieval_id = response["retrieval_id"]

            # Poll cho kết quả (timeout 30s)
            retrieval_result = None
            for _ in range(15):
                try:
                    retrieval_result = client.get_retrieval(retrieval_id)
                    status = retrieval_result.get("status", "")
                    if status == "completed":
                        break
                    elif status == "failed":
                        retrieval_result = None
                        break
                except Exception:
                    pass
                time.sleep(2)

            if not retrieval_result:
                continue

            # Parse retrieved nodes thành SearchResult
            nodes = retrieval_result.get("retrieved_nodes", [])
            if not nodes:
                nodes = retrieval_result.get("nodes", [])
            if not nodes:
                # Thử lấy từ kết quả trực tiếp nếu API format khác
                content = retrieval_result.get("content", "")
                if content:
                    nodes = [{"content": content}]

            for rank, node in enumerate(nodes):
                node_content = node.get("content", "") or node.get("text", "")
                if not node_content or not node_content.strip():
                    continue

                # Tạo ID ổn định từ source + rank
                result_id = f"pageindex::{source_key}::node-{rank}"
                # Score giảm dần theo rank nếu API không trả score
                node_score = node.get("score", 1.0 / (rank + 1))

                # Xác định doc_type từ source path
                doc_type = "legal" if "legal" in source_key else "news"

                all_results.append({
                    "id": result_id,
                    "content": node_content.strip(),
                    "score": float(node_score),
                    "metadata": {
                        "source": source_key.split("/")[-1],
                        "title": Path(source_key).stem,
                        "doc_type": doc_type,
                        "url": None,
                        "chunk_index": rank,
                    },
                    "retrieval_method": "pageindex",
                })
        except Exception:
            # Bỏ qua lỗi từng document, tiếp tục với các document khác
            continue

    # Sort theo score giảm dần, deduplicate theo id, cắt top_k
    all_results.sort(key=lambda x: x["score"], reverse=True)
    seen_ids: set[str] = set()
    unique_results: list[dict] = []
    for item in all_results:
        if item["id"] not in seen_ids:
            seen_ids.add(item["id"])
            unique_results.append(item)
    return unique_results[:top_k]


if __name__ == "__main__":
    if PAGEINDEX_API_KEY:
        upload_documents()
        results = pageindex_search("học phí", top_k=3)
        for r in results:
            print(f"  {r['id']}  score={r['score']:.4f}")
    else:
        print("PAGEINDEX_API_KEY not set. Skipping.")
        print("Set it in .env to use PageIndex vectorless fallback.")
