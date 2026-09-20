"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.

Ghi chú thiết kế:
    - SDK chỉ nhận PDF nên upload thẳng PDF gốc ở data/landing/legal/ thay vì
      convert Markdown, vừa đỡ hỏng dấu tiếng Việt vừa giữ được số trang.
    - Chỉ upload nhóm legal: đây là các văn bản dài 30+ trang mà dense search
      hay trượt, đúng chỗ vectorless phát huy. News đã đủ ngắn cho dense/BM25.
    - SDK gọi requests không đặt timeout, nên mọi lời gọi mạng được bọc deadline.
"""

import concurrent.futures
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
LANDING_LEGAL_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
LEGAL_SOURCES_PATH = Path(__file__).parent.parent / "data" / "legal_sources.json"
CACHE_PATH = Path(__file__).parent.parent / "pageindex_doc_ids.json"

# Ngân sách thời gian cho toàn bộ một lần fallback (giây).
SEARCH_TIMEOUT = float(os.getenv("PAGEINDEX_TIMEOUT") or 25.0)
# Timeout cho từng lời gọi HTTP lẻ.
CALL_TIMEOUT = 10.0
# Poll thưa tay: gói free rate-limit theo số request, poll 1s/lần với nhiều
# tài liệu song song là dính 429 ngay.
POLL_INTERVAL = 2.5
FIRST_POLL_DELAY = 2.0
RATE_LIMIT_BACKOFF = 5.0


def _call(func, *args, timeout: float = CALL_TIMEOUT, **kwargs):
    """Gọi SDK có timeout vì PageIndexClient không tự đặt timeout cho requests."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(func, *args, **kwargs).result(timeout=timeout)


def _retry_after(message: str) -> float | None:
    """Đọc 'Try again in 24 seconds' từ thông báo rate limit."""
    match = re.search(r"try again in (\d+)", message.lower())
    return float(match.group(1)) if match else None


def _call_resilient(func, *args, deadline: float, **kwargs):
    """Như _call nhưng chờ và thử lại khi bị rate limit, trong giới hạn deadline."""
    while True:
        try:
            return _call(func, *args, **kwargs)
        except Exception as error:
            message = str(error).lower()
            if "rate limit" not in message and "429" not in message:
                raise
            remaining = deadline - time.monotonic()
            wait = _retry_after(message) or RATE_LIMIT_BACKOFF
            if wait >= remaining:
                raise
            time.sleep(wait)


def _get_client():
    """Khởi tạo client, raise nếu thiếu API key."""
    if not PAGEINDEX_API_KEY.strip():
        raise RuntimeError("Thiếu PAGEINDEX_API_KEY trong .env")
    from pageindex import PageIndexClient

    return PageIndexClient(PAGEINDEX_API_KEY)


def _load_legal_metadata() -> dict[str, dict]:
    """Đọc manifest để gắn title/url thật cho từng PDF."""
    if not LEGAL_SOURCES_PATH.exists():
        return {}
    manifest = json.loads(LEGAL_SOURCES_PATH.read_text(encoding="utf-8"))
    return {item["filename"]: item for item in manifest}


def _load_cache() -> dict[str, dict]:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict[str, dict]) -> None:
    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    client = _get_client()
    metadata = _load_legal_metadata()
    cache = _load_cache()

    pdfs = sorted(LANDING_LEGAL_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"[task8] Không tìm thấy PDF nào trong {LANDING_LEGAL_DIR}")
        return

    for path in pdfs:
        if path.name in cache and cache[path.name].get("doc_id"):
            print(f"[task8] Bỏ qua (đã upload): {path.name}")
            continue

        source = metadata.get(path.name, {})
        try:
            response = _call(client.submit_document, str(path), timeout=120.0)
        except Exception as error:
            print(f"[task8] Upload lỗi {path.name}: {error}")
            continue

        doc_id = response.get("doc_id") if isinstance(response, dict) else None
        if not doc_id:
            print(f"[task8] Response không có doc_id cho {path.name}: {response}")
            continue

        cache[path.name] = {
            "doc_id": doc_id,
            "title": source.get("title", path.stem),
            "url": source.get("landing_page") or source.get("url"),
        }
        print(f"[task8] Đã upload {path.name} -> {doc_id}")
        _save_cache(cache)

    _save_cache(cache)
    print(f"[task8] Cache: {CACHE_PATH.name} ({len(cache)} tài liệu)")


def _extract_nodes(payload: object) -> list[dict]:
    """Lấy danh sách node từ response, chấp nhận vài biến thể tên field."""
    if not isinstance(payload, dict):
        return []
    for key in ("retrieved_nodes", "retrieval", "results", "nodes", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [node for node in value if isinstance(node, dict)]
        # Một số response bọc thêm một lớp: {"retrieval": {"nodes": [...]}}
        if isinstance(value, dict):
            nested = _extract_nodes(value)
            if nested:
                return nested
    return []


def _flatten(value: object) -> list[dict | str]:
    """Duỗi cấu trúc lồng nhau: relevant_contents là list-của-list-của-dict."""
    if isinstance(value, list):
        flat: list[dict | str] = []
        for part in value:
            flat.extend(_flatten(part))
        return flat
    if isinstance(value, (dict, str)):
        return [value]
    return []


def _node_fragments(node: dict) -> list[dict]:
    """Trả về các mảnh nội dung của node, chuẩn hoá về dict."""
    for key in ("relevant_contents", "relevant_content", "contents", "content", "text"):
        fragments = [
            {"relevant_content": part} if isinstance(part, str) else part
            for part in _flatten(node.get(key))
        ]
        fragments = [
            fragment
            for fragment in fragments
            if str(fragment.get("relevant_content") or fragment.get("content") or "").strip()
        ]
        if fragments:
            return fragments
    return []


def _fragment_text(fragment: dict) -> str:
    return str(fragment.get("relevant_content") or fragment.get("content") or "").strip()


def _node_page(fragments: list[dict], node: dict) -> int | None:
    """Lấy số trang: API trả dạng '<physical_index_9>' chứ không phải số."""
    candidates = [fragment.get("physical_index") for fragment in fragments]
    candidates += [node.get("page_index"), node.get("page"), node.get("physical_index")]
    for candidate in candidates:
        if isinstance(candidate, int) and candidate >= 0:
            return candidate
        if isinstance(candidate, str):
            digits = re.search(r"\d+", candidate)
            if digits:
                return int(digits.group())
    return None


def _wait_for_retrieval(client, retrieval_id: str, deadline: float) -> dict:
    """Poll cho tới khi retrieval xong hoặc hết ngân sách thời gian."""
    # Kết quả không bao giờ sẵn ngay, poll lần đầu luôn phí một request.
    time.sleep(min(FIRST_POLL_DELAY, max(0.0, deadline - time.monotonic())))
    while time.monotonic() < deadline:
        payload = _call_resilient(client.get_retrieval, retrieval_id, deadline=deadline)
        status = str(payload.get("status", "")).lower() if isinstance(payload, dict) else ""
        if status in {"completed", "complete", "done", "success", "finished", ""}:
            return payload if isinstance(payload, dict) else {}
        if status in {"failed", "error"}:
            raise RuntimeError(f"PageIndex retrieval thất bại: {payload}")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError("PageIndex retrieval quá hạn")


def _retrieve_one(client, doc_id: str, query: str, deadline: float) -> dict:
    """Submit rồi chờ kết quả retrieval của đúng một tài liệu."""
    submitted = _call_resilient(client.submit_query, doc_id, query, deadline=deadline)
    retrieval_id = submitted.get("retrieval_id") if isinstance(submitted, dict) else None
    if not retrieval_id:
        return {}
    return _wait_for_retrieval(client, retrieval_id, deadline)


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    cache = _load_cache()
    if not cache:
        # Chưa upload hoặc chưa cấu hình key: coi như fallback không khả dụng,
        # Task 9 sẽ tự quay về hybrid thay vì vỡ pipeline.
        print("[task8] Chưa có pageindex_doc_ids.json, bỏ qua fallback")
        return []

    try:
        client = _get_client()
    except RuntimeError as error:
        print(f"[task8] {error}")
        return []

    deadline = time.monotonic() + SEARCH_TIMEOUT

    # Query song song từng tài liệu: chạy tuần tự thì 3 văn bản cộng dồn sẽ
    # vượt ngân sách, tài liệu cuối luôn bị cắt.
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(len(cache), 1)) as pool:
        futures = {
            pool.submit(_retrieve_one, client, entry["doc_id"], query, deadline): filename
            for filename, entry in cache.items()
            if entry.get("doc_id")
        }
        payloads: dict[str, dict] = {}
        for future in concurrent.futures.as_completed(futures):
            filename = futures[future]
            try:
                payloads[filename] = future.result()
            except Exception as error:
                # Một tài liệu lỗi không được làm hỏng các tài liệu còn lại.
                print(f"[task8] Truy vấn lỗi trên {filename}: {error}")

    results: list[dict] = []
    for filename, payload in payloads.items():
        entry = cache[filename]
        for rank, node in enumerate(_extract_nodes(payload), 1):
            fragments = _node_fragments(node)
            content = "\n".join(_fragment_text(fragment) for fragment in fragments)
            if not content.strip():
                continue

            node_id = str(node.get("node_id") or node.get("id") or rank)
            page = _node_page(fragments, node)
            score = node.get("relevance_score", node.get("score"))
            # Tên Điều/Khoản để Task 10 trích dẫn được tới mục cụ thể.
            section = str(
                node.get("title")
                or (fragments[0].get("section_title") if fragments else "")
                or ""
            ).strip()

            results.append(
                {
                    "id": f"{filename}::pageindex-{node_id}",
                    "content": content,
                    # API retrieval không trả score: dùng thang giảm dần theo rank
                    # để giữ đúng contract "sort giảm dần".
                    "score": float(score)
                    if isinstance(score, (int, float)) and not isinstance(score, bool)
                    else max(0.0, 1.0 - 0.05 * rank),
                    "metadata": {
                        "source": filename,
                        "title": entry.get("title") or filename,
                        "doc_type": "legal",
                        "url": entry.get("url"),
                        # Không có chunk_index thật: dùng số trang làm mốc định vị,
                        # lùi về rank khi tài liệu không trả physical_index.
                        "chunk_index": page if page is not None else rank - 1,
                        "section": section,
                        "page": page,
                    },
                    "retrieval_method": "pageindex",
                }
            )

    # Khử trùng ID rồi sort giảm dần theo contract SearchResult.
    unique: dict[str, dict] = {}
    for item in results:
        if item["id"] not in unique or item["score"] > unique[item["id"]]["score"]:
            unique[item["id"]] = item
    ranked = sorted(unique.values(), key=lambda item: item["score"], reverse=True)
    return ranked[: max(top_k, 0)]


if __name__ == "__main__":
    try:
        upload_documents()
    except RuntimeError as error:
        print(f"[task8] {error}")
        print(
            "[task8] Lấy key tại https://dash.pageindex.ai rồi điền vào .env:\n"
            "        PAGEINDEX_API_KEY=..."
        )
