"""
Task 8 — PageIndex vectorless fallback.

Dùng PageIndex Cloud REST API để upload PDF và search bằng LLM reasoning
thay vì vector similarity. Đây là fallback khi dense cosine score thấp.

Flow:
    1. Upload PDF gốc từ data/landing/legal/ lên PageIndex Cloud.
    2. Cache doc_id vào file JSON cục bộ để không upload lại.
    3. Gọi Chat API với danh sách doc_id để search.
    4. Parse response thành list[SearchResult].

Lưu ý: PAGEINDEX_API_KEY không có → trả list rỗng (không crash pipeline).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")

LANDING_LEGAL_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

# Cache file lưu mapping filename -> doc_id để không upload lại mỗi lần chạy.
_CACHE_FILE = Path(__file__).parent.parent / "data" / ".pageindex_doc_ids.json"

_BASE_URL = "https://api.pageindex.ai"
_TIMEOUT = 30  # seconds


def _headers() -> dict[str, str]:
    return {"api_key": PAGEINDEX_API_KEY}


def _load_cache() -> dict[str, str]:
    """Đọc cache doc_id từ file JSON."""
    if _CACHE_FILE.exists():
        try:
            return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _save_cache(cache: dict[str, str]) -> None:
    """Ghi cache doc_id ra file JSON."""
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _upload_pdf(path: Path) -> str | None:
    """Upload một file PDF lên PageIndex, trả về doc_id hoặc None nếu lỗi."""
    try:
        with open(path, "rb") as f:
            response = requests.post(
                f"{_BASE_URL}/doc/",
                headers=_headers(),
                files={"file": (path.name, f, "application/pdf")},
                timeout=_TIMEOUT,
            )
        response.raise_for_status()
        doc_id: str = response.json()["doc_id"]
        print(f"[task8] Uploaded '{path.name}' → doc_id={doc_id}")
        return doc_id
    except Exception as exc:
        print(f"[task8] Lỗi upload '{path.name}': {exc}")
        return None


def _wait_until_ready(doc_id: str, max_wait: int = 120) -> bool:
    """Chờ document xử lý xong (status=completed). Trả False nếu timeout."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            resp = requests.get(
                f"{_BASE_URL}/doc/{doc_id}/",
                headers=_headers(),
                params={"type": "tree"},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            status = resp.json().get("status", "")
            if status == "completed":
                return True
            if status == "failed":
                print(f"[task8] doc_id={doc_id} processing failed.")
                return False
        except Exception as exc:
            print(f"[task8] Lỗi kiểm tra status {doc_id}: {exc}")
            return False
        time.sleep(5)
    print(f"[task8] Timeout chờ doc_id={doc_id}.")
    return False


def upload_documents() -> dict[str, str]:
    """Upload tất cả PDF trong data/landing/legal/ và cache doc_id.

    Chỉ upload file chưa có trong cache. Trả về mapping filename -> doc_id.
    Không raise — lỗi từng file được bắt riêng.
    """
    if not PAGEINDEX_API_KEY:
        print("[task8] PAGEINDEX_API_KEY chưa set, bỏ qua upload.")
        return {}

    cache = _load_cache()

    pdf_paths = sorted(
        p for p in LANDING_LEGAL_DIR.iterdir()
        if p.is_file() and p.suffix.lower() == ".pdf" and not p.name.startswith(".")
    )
    if not pdf_paths:
        print(f"[task8] Không tìm thấy PDF nào trong {LANDING_LEGAL_DIR}.")
        return cache

    for path in pdf_paths:
        if path.name in cache:
            print(f"[task8] '{path.name}' đã upload (doc_id={cache[path.name]}), bỏ qua.")
            continue

        doc_id = _upload_pdf(path)
        if doc_id:
            # Chờ xử lý xong trước khi dùng để search.
            _wait_until_ready(doc_id, max_wait=120)
            cache[path.name] = doc_id
            _save_cache(cache)

    return cache


def _get_doc_ids() -> list[str]:
    """Lấy danh sách doc_id từ cache. Upload nếu cache rỗng."""
    cache = _load_cache()
    if not cache and PAGEINDEX_API_KEY:
        cache = upload_documents()
    return list(cache.values())


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult bằng cách gọi PageIndex Chat API.

    Dùng Chat API với list doc_id để search across all uploaded documents.
    Parse answer thành SearchResult với score giảm dần theo rank (PageIndex
    không trả raw score, dùng rank-based score: 1/(1+rank)).

    Trả list rỗng nếu API key không có hoặc gặp lỗi — không crash pipeline.
    """
    if not PAGEINDEX_API_KEY:
        print("[task8] PAGEINDEX_API_KEY chưa set, trả list rỗng.")
        return []

    doc_ids = _get_doc_ids()
    if not doc_ids:
        print("[task8] Không có doc_id nào, trả list rỗng.")
        return []

    try:
        # Yêu cầu LLM trả về các đoạn văn bản liên quan từ tài liệu
        system_instruction = (
            "Tìm và trích dẫn trực tiếp các đoạn văn bản liên quan nhất từ tài liệu "
            f"để trả lời câu hỏi. Trả về tối đa {top_k} đoạn, mỗi đoạn trên một dòng mới "
            "bắt đầu bằng '- '. Chỉ trích dẫn, không giải thích thêm."
        )
        response = requests.post(
            f"{_BASE_URL}/chat/completions",
            headers={**_headers(), "Content-Type": "application/json"},
            json={
                "doc_id": doc_ids,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": query},
                ],
                "stream": False,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        answer: str = data["choices"][0]["message"]["content"]
    except Exception as exc:
        print(f"[task8] Lỗi gọi PageIndex Chat API: {exc}")
        return []

    # Parse answer thành list[SearchResult].
    # Mỗi dòng bắt đầu bằng "- " là một chunk riêng.
    lines = [
        line.lstrip("- ").strip()
        for line in answer.splitlines()
        if line.strip().startswith("- ") or (line.strip() and not line.strip().startswith("#"))
    ]
    # Lấy top_k dòng không rỗng
    chunks = [line for line in lines if line][:top_k]

    if not chunks:
        # Fallback: toàn bộ answer là một chunk
        chunks = [answer.strip()[:1000]] if answer.strip() else []

    results: list[dict] = []
    for rank, content in enumerate(chunks):
        # Rank-based score: chunk đầu tiên score cao nhất
        score = 1.0 / (1.0 + rank)
        results.append({
            "id": f"pageindex::result-{rank}",
            "content": content,
            "score": score,
            "metadata": {
                "source": "pageindex",
                "title": "PageIndex Search Result",
                "doc_type": "legal",
                "url": None,
                "chunk_index": rank,
            },
            "retrieval_method": "pageindex",
        })

    return results


if __name__ == "__main__":
    print("[task8] Uploading documents...")
    doc_map = upload_documents()
    print(f"[task8] doc_ids: {doc_map}")

    print("\n[task8] Testing search...")
    results = pageindex_search("điều kiện mua bán nhà ở", top_k=3)
    for r in results:
        print(f"  [{r['score']:.3f}] {r['id']}")
        print(f"  {r['content'][:150]}...")
