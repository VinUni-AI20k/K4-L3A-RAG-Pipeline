"""
Task 8 — PageIndex vectorless fallback.

PageIndex (api.pageindex.ai) dựng cây mục lục cho tài liệu và cho LLM duyệt cây
để tìm đoạn liên quan, không cần embedding. Task 9 dùng nó khi dense search
không đủ tự tin.

Luồng:
    1. upload_documents(): legal PDF gửi nguyên bản; news Markdown chuyển sang PDF
       bằng fpdf2 rồi gửi. doc_id được cache trong pageindex_doc_ids.json để
       chạy lại không upload lại.
    2. pageindex_search(): gửi query tới từng doc đã upload, poll kết quả trong
       một deadline tổng, parse node thành SearchResult method "pageindex".

SDK pageindex 0.2.8 gọi requests không có timeout, nên đường query (chạy trong
UI) tự gọi HTTP với timeout thay vì qua SDK. Đường upload (chạy tay một lần)
dùng SDK vì có multipart sẵn.

Không có PAGEINDEX_API_KEY hoặc chưa upload: pageindex_search trả [] và pipeline
tiếp tục với kết quả hybrid — không được làm UI crash.

Chạy:
    python -m src.task8_pageindex_vectorless            # upload
    python -m src.task8_pageindex_vectorless "câu hỏi"  # thử query
"""

import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
BASE_URL = "https://api.pageindex.ai"

ROOT = Path(__file__).parent.parent
STANDARDIZED_DIR = ROOT / "data" / "standardized"
LANDING_LEGAL_DIR = ROOT / "data" / "landing" / "legal"
PDF_DIR = ROOT / "pageindex_pdfs"
DOC_IDS_PATH = ROOT / "pageindex_doc_ids.json"

HTTP_TIMEOUT = 20          # giây cho một HTTP call
QUERY_DEADLINE = 45        # giây tổng cho một lần pageindex_search
POLL_INTERVAL = 1.5
MAX_DOCS_PER_QUERY = int(os.getenv("PAGEINDEX_MAX_DOCS", "3"))

UNICODE_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


# --------------------------------------------------------------------------- #
# Cache doc_id
# --------------------------------------------------------------------------- #

def _load_doc_ids() -> dict[str, dict]:
    if DOC_IDS_PATH.exists():
        return json.loads(DOC_IDS_PATH.read_text(encoding="utf-8"))
    return {}


def _save_doc_ids(mapping: dict[str, dict]) -> None:
    DOC_IDS_PATH.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


# --------------------------------------------------------------------------- #
# Chuẩn bị PDF
# --------------------------------------------------------------------------- #

def _read_standardized(path: Path) -> tuple[dict[str, str], str]:
    raw = path.read_text(encoding="utf-8")
    match = FRONT_MATTER.match(raw)
    if not match:
        return {}, raw
    fields = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, raw[match.end():]


def _markdown_to_pdf(title: str, body: str, output: Path) -> None:
    """PDF văn bản thuần, đủ để PageIndex OCR và dựng cây theo heading."""
    from fpdf import FPDF, XPos, YPos

    # fpdf2 >= 2.5 để con trỏ ở mép phải sau multi_cell; ô kế tiếp w=0 sẽ rộng 0
    # và treo/ném lỗi. Luôn đưa con trỏ về lề trái, xuống dòng.
    cell = dict(new_x=XPos.LMARGIN, new_y=YPos.NEXT, wrapmode="CHAR")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    font = next((f for f in UNICODE_FONTS if Path(f).exists()), None)
    if font:
        pdf.add_font("body", "", font)
        family = "body"
    else:
        family = "Helvetica"
        # Core font chỉ có Latin-1; bỏ ký tự ngoài bảng thay vì crash.
        body = body.encode("latin-1", "replace").decode("latin-1")
        title = title.encode("latin-1", "replace").decode("latin-1")

    pdf.set_font(family, size=16)
    pdf.multi_cell(0, 8, title, **cell)
    pdf.ln(4)

    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            pdf.ln(3)
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        if 0 < level <= 3 and stripped.startswith("#"):
            pdf.set_font(family, size=15 - level)
            pdf.multi_cell(0, 7, stripped.lstrip("#").strip(), **cell)
            pdf.set_font(family, size=10)
        else:
            pdf.set_font(family, size=10)
            pdf.multi_cell(0, 5, stripped, **cell)

    output.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output))


def _documents_to_upload() -> list[dict]:
    """Mỗi phần tử: key (id ổn định), pdf_path, và metadata theo contract."""
    items = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        fields, body = _read_standardized(path)
        key = path.relative_to(STANDARDIZED_DIR).with_suffix("").as_posix()
        doc_type = fields.get("doc_type") or ("legal" if "legal" in path.parts else "news")
        metadata = {
            "source": fields.get("source") or path.name,
            "title": fields.get("title") or path.stem,
            "doc_type": doc_type,
            "url": fields.get("url") or None,
        }

        original = LANDING_LEGAL_DIR / metadata["source"]
        if doc_type == "legal" and original.suffix.lower() == ".pdf" and original.exists():
            pdf_path = original          # PDF gốc giữ layout tốt hơn bản convert
        else:
            pdf_path = PDF_DIR / f"{path.stem}.pdf"
            if not pdf_path.exists():
                _markdown_to_pdf(metadata["title"], body, pdf_path)

        items.append({"key": key, "pdf_path": pdf_path, "metadata": metadata})
    return items


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    if not PAGEINDEX_API_KEY:
        print("Bỏ qua: chưa có PAGEINDEX_API_KEY trong .env")
        return

    from pageindex import PageIndexAPIError, PageIndexClient

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
    cache = _load_doc_ids()
    uploaded = 0

    for item in _documents_to_upload():
        if item["key"] in cache:
            print(f"Skip (đã có): {item['key']} -> {cache[item['key']]['doc_id']}")
            continue
        try:
            response = client.submit_document(str(item["pdf_path"]))
        except (PageIndexAPIError, OSError) as error:
            print(f"FAIL {item['key']}: {error}")
            continue

        doc_id = response.get("doc_id")
        if not doc_id:
            print(f"FAIL {item['key']}: response không có doc_id: {response}")
            continue

        cache[item["key"]] = {"doc_id": doc_id, **item["metadata"]}
        _save_doc_ids(cache)
        uploaded += 1
        print(f"OK   {item['key']} -> {doc_id}")

    print(f"\nUpload mới: {uploaded}, tổng trong cache: {len(cache)} -> {DOC_IDS_PATH.name}")
    print("PageIndex xử lý bất đồng bộ; đợi vài phút trước khi query.")


# --------------------------------------------------------------------------- #
# Query
# --------------------------------------------------------------------------- #

def _headers() -> dict[str, str]:
    return {"api_key": PAGEINDEX_API_KEY}


def _submit_query(doc_id: str, query: str) -> str:
    response = requests.post(
        f"{BASE_URL}/retrieval/",
        headers=_headers(),
        json={"doc_id": doc_id, "query": query, "thinking": False},
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()
    retrieval_id = response.json().get("retrieval_id")
    if not retrieval_id:
        raise RuntimeError(f"PageIndex không trả retrieval_id cho doc {doc_id}")
    return retrieval_id


def _poll_retrieval(retrieval_id: str, deadline: float) -> dict:
    while True:
        response = requests.get(
            f"{BASE_URL}/retrieval/{retrieval_id}/",
            headers=_headers(),
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        status = str(payload.get("status", "")).lower()
        if status in {"completed", "done", "success", "succeeded"}:
            return payload
        if status in {"failed", "error"}:
            raise RuntimeError(f"PageIndex retrieval thất bại: {payload}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"PageIndex quá {QUERY_DEADLINE}s chưa trả kết quả")
        time.sleep(POLL_INTERVAL)


def _node_text(node: dict) -> str:
    """Tên field nội dung chưa được xác nhận với key thật; thử các tên phổ biến."""
    for key in ("relevant_contents", "content", "text", "summary"):
        value = node.get(key)
        if isinstance(value, list):
            value = "\n".join(str(v) for v in value if v)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def parse_retrieval(payload: dict, doc_key: str, metadata: dict) -> list[dict]:
    """Chuyển node của PageIndex thành SearchResult; score giảm dần theo rank."""
    nodes = payload.get("retrieved_nodes") or payload.get("nodes") or payload.get("results") or []
    results = []
    for rank, node in enumerate(nodes, 1):
        content = _node_text(node)
        if not content:
            continue
        node_id = node.get("node_id") or node.get("id") or f"node-{rank}"
        title = node.get("title")
        results.append({
            "id": f"{doc_key}::pageindex-{node_id}",
            "content": f"{metadata['title']} > {title}\n{content}" if title else content,
            "score": 1.0 / rank,
            "metadata": {**metadata, "chunk_index": rank - 1},
            "retrieval_method": "pageindex",
        })
    return results


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if not PAGEINDEX_API_KEY or top_k <= 0 or not query.strip():
        return []

    cache = _load_doc_ids()
    if not cache:
        return []

    deadline = time.monotonic() + QUERY_DEADLINE
    # Gửi tất cả query trước rồi mới poll, để các doc được xử lý song song.
    pending = []
    for doc_key, entry in list(cache.items())[:MAX_DOCS_PER_QUERY]:
        retrieval_id = _submit_query(entry["doc_id"], query)
        pending.append((doc_key, entry, retrieval_id))

    results: list[dict] = []
    for doc_key, entry, retrieval_id in pending:
        payload = _poll_retrieval(retrieval_id, deadline)
        metadata = {key: entry.get(key) for key in ("source", "title", "doc_type", "url")}
        results.extend(parse_retrieval(payload, doc_key, metadata))

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print(f"Query: {question}\n")
        for rank, result in enumerate(pageindex_search(question, top_k=5), 1):
            print(f"{rank}. score={result['score']:.3f}  {result['content'][:100]}")
    else:
        upload_documents()
