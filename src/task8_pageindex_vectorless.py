"""
Task 8 — PageIndex vectorless fallback.

Upload các tài liệu PDF lên PageIndex, lưu document ID để không upload lại,
sau đó dùng Retrieval API để lấy nội dung liên quan.
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from pageindex import PageIndexAPIError, PageIndexClient


load_dotenv()

LOGGER = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent
LANDING_LEGAL_DIR = ROOT_DIR / "data" / "landing" / "legal"
CACHE_PATH = ROOT_DIR / "data" / "pageindex_document_ids.json"

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "").strip()

REQUEST_TIMEOUT_SECONDS = 30
PROCESSING_TIMEOUT_SECONDS = 300
POLL_INTERVAL_SECONDS = 2


def _has_usable_api_key() -> bool:
    """Return False for an empty key or a common placeholder value."""

    if not PAGEINDEX_API_KEY:
        return False

    normalized = PAGEINDEX_API_KEY.casefold()
    placeholder_markers = (
        "your_",
        "your-",
        "paste_",
        "paste-",
        "dan_key",
        "dán_key",
        "<pageindex",
    )
    return not normalized.startswith(placeholder_markers)


class TimedPageIndexClient(PageIndexClient):
    """
    PageIndexClient có HTTP timeout.

    PageIndex SDK 0.2.8 không truyền timeout vào requests, vì vậy các method
    cần dùng trong bài được override để tránh treo ứng dụng vô thời hạn.
    """

    def submit_document(self, file_path: str) -> dict[str, Any]:
        with open(file_path, "rb") as file_handle:
            response = requests.post(
                f"{self.BASE_URL}/doc/",
                headers=self._headers(),
                files={"file": file_handle},
                data={"if_retrieval": True},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

        if response.status_code != 200:
            raise PageIndexAPIError(
                f"Failed to submit document: {response.text}"
            )

        return response.json()

    def get_tree(
        self,
        doc_id: str,
        node_summary: bool = False,
    ) -> dict[str, Any]:
        response = requests.get(
            f"{self.BASE_URL}/doc/{doc_id}/",
            headers=self._headers(),
            params={
                "type": "tree",
                "summary": str(node_summary).lower(),
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:
            raise PageIndexAPIError(
                f"Failed to get tree result: {response.text}"
            )

        return response.json()

    def submit_query(
        self,
        doc_id: str,
        query: str,
        thinking: bool = False,
    ) -> dict[str, Any]:
        response = requests.post(
            f"{self.BASE_URL}/retrieval/",
            headers=self._headers(),
            json={
                "doc_id": doc_id,
                "query": query,
                "thinking": thinking,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:
            raise PageIndexAPIError(
                f"Failed to submit retrieval: {response.text}"
            )

        return response.json()

    def get_retrieval(self, retrieval_id: str) -> dict[str, Any]:
        response = requests.get(
            f"{self.BASE_URL}/retrieval/{retrieval_id}/",
            headers=self._headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:
            raise PageIndexAPIError(
                f"Failed to get retrieval result: {response.text}"
            )

        return response.json()


def _create_client() -> TimedPageIndexClient:
    if not _has_usable_api_key():
        raise RuntimeError("PAGEINDEX_API_KEY is not configured")

    return TimedPageIndexClient(api_key=PAGEINDEX_API_KEY)


def _file_hash(path: Path) -> str:
    """Tạo SHA-256 để nhận biết tài liệu đã thay đổi."""

    digest = hashlib.sha256()

    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def _load_cache() -> dict[str, dict]:
    if not CACHE_PATH.exists():
        return {}

    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    return data if isinstance(data, dict) else {}


def _save_cache(cache: dict[str, dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = CACHE_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(CACHE_PATH)


def _wait_until_document_ready(
    client: TimedPageIndexClient,
    doc_id: str,
) -> None:
    deadline = time.monotonic() + PROCESSING_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        tree_result = client.get_tree(doc_id)

        if tree_result.get("retrieval_ready") is True:
            return

        status = str(tree_result.get("status", "")).lower()

        if status in {"failed", "error"}:
            raise PageIndexAPIError(
                f"PageIndex processing failed for document {doc_id}"
            )

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(
        f"PageIndex processing timed out for document {doc_id}"
    )


def _wait_for_retrieval(
    client: TimedPageIndexClient,
    retrieval_id: str,
) -> dict:
    deadline = time.monotonic() + PROCESSING_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        result = client.get_retrieval(retrieval_id)
        status = str(result.get("status", "")).lower()

        if status == "completed":
            return result

        if status in {"failed", "error"}:
            raise PageIndexAPIError(
                f"PageIndex retrieval failed: {retrieval_id}"
            )

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(
        f"PageIndex retrieval timed out: {retrieval_id}"
    )


def upload_documents() -> None:
    """
    Upload các PDF chưa có trên PageIndex.

    Cache gồm document ID và hash của file. Nếu file không đổi thì không upload
    lại. PageIndex SDK 0.2.8 chủ yếu hỗ trợ PDF, vì vậy dùng tài liệu gốc trong
    data/landing/legal.
    """

    if not _has_usable_api_key():
        print(
            "Skipping PageIndex upload: "
            "PAGEINDEX_API_KEY is not configured."
        )
        return

    client = _create_client()
    LANDING_LEGAL_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(LANDING_LEGAL_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF documents found in: {LANDING_LEGAL_DIR}")
        return

    cache = _load_cache()

    for path in pdf_files:
        source_key = path.name
        fingerprint = _file_hash(path)
        cached = cache.get(source_key, {})

        if (
            cached.get("doc_id")
            and cached.get("sha256") == fingerprint
        ):
            print(f"Skipped unchanged document: {path.name}")
            continue

        try:
            response = client.submit_document(str(path))
            doc_id = response.get("doc_id")

            if not isinstance(doc_id, str) or not doc_id.strip():
                raise PageIndexAPIError(
                    f"PageIndex did not return doc_id for {path.name}"
                )

            cache[source_key] = {
                "doc_id": doc_id,
                "sha256": fingerprint,
                "source": path.name,
                "title": path.stem,
                "doc_type": "legal",
                "url": None,
            }

            # Lưu ngay sau upload để không upload lại nếu polling bị gián đoạn.
            _save_cache(cache)

            print(f"Uploaded: {path.name} -> {doc_id}")
            _wait_until_document_ready(client, doc_id)
            print(f"Ready: {path.name}")

        except Exception as error:
            LOGGER.warning("PageIndex upload failed for %s: %s", path, error)
            print(f"Failed: {path.name} — {error}")


def _normalise_page_index(value: object, fallback: int) -> int:
    if isinstance(value, int) and value >= 0:
        return value

    if isinstance(value, str) and value.isdigit():
        return int(value)

    return fallback


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Trả về PageIndex SearchResult.

    Nếu API key, cache hoặc provider không sẵn sàng thì trả danh sách rỗng để
    retrieval pipeline có thể quay lại kết quả hybrid.
    """

    query = query.strip()

    if not query or top_k <= 0 or not _has_usable_api_key():
        return []

    cache = _load_cache()

    if not cache:
        return []

    try:
        client = _create_client()
    except Exception:
        return []

    collected: list[dict] = []
    seen_ids: set[str] = set()
    global_rank = 0

    for source_info in cache.values():
        doc_id = source_info.get("doc_id")

        if not isinstance(doc_id, str) or not doc_id:
            continue

        try:
            if not client.is_retrieval_ready(doc_id):
                continue

            submitted = client.submit_query(
                doc_id=doc_id,
                query=query,
                thinking=True,
            )
            retrieval_id = submitted.get("retrieval_id")

            if not isinstance(retrieval_id, str) or not retrieval_id:
                continue

            response = _wait_for_retrieval(client, retrieval_id)
            nodes = response.get("retrieved_nodes", [])

            if not isinstance(nodes, list):
                continue

            for node_position, node in enumerate(nodes):
                if not isinstance(node, dict):
                    continue

                node_id = str(
                    node.get("node_id")
                    or node.get("id")
                    or f"node-{node_position}"
                )
                node_title = str(
                    node.get("title")
                    or source_info.get("title")
                    or source_info.get("source")
                    or "Unknown"
                )

                relevant_contents = node.get("relevant_contents", [])

                if not isinstance(relevant_contents, list):
                    continue

                for content_position, content_item in enumerate(
                    relevant_contents
                ):
                    if not isinstance(content_item, dict):
                        continue

                    content = (
                        content_item.get("relevant_content")
                        or content_item.get("content")
                        or content_item.get("text")
                    )

                    if not isinstance(content, str) or not content.strip():
                        continue

                    page_index = _normalise_page_index(
                        content_item.get("page_index"),
                        fallback=content_position,
                    )

                    result_id = (
                        f"pageindex::{doc_id}::{node_id}::{page_index}"
                        f"::{content_position}"
                    )

                    if result_id in seen_ids:
                        continue

                    seen_ids.add(result_id)
                    global_rank += 1

                    collected.append(
                        {
                            "id": result_id,
                            "content": content.strip(),
                            # PageIndex 0.2.8 không bảo đảm trả score.
                            # Dùng reciprocal rank để có score giảm dần.
                            "score": 1.0 / global_rank,
                            "metadata": {
                                "source": str(
                                    source_info.get("source", "Unknown")
                                ),
                                "title": node_title,
                                "doc_type": str(
                                    source_info.get("doc_type", "legal")
                                ),
                                "url": source_info.get("url"),
                                "chunk_index": page_index,
                            },
                            "retrieval_method": "pageindex",
                        }
                    )

        except Exception as error:
            # Một document lỗi không được làm toàn bộ UI crash.
            LOGGER.warning(
                "PageIndex search failed for document %s: %s",
                doc_id,
                error,
            )
            continue

    return sorted(
        collected,
        key=lambda item: item["score"],
        reverse=True,
    )[:top_k]


if __name__ == "__main__":
    upload_documents()
