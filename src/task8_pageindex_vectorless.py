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
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent
PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = ROOT_DIR / "data" / "standardized"
LEGAL_LANDING_DIR = ROOT_DIR / "data" / "landing" / "legal"
DOC_IDS_FILE = ROOT_DIR / "pageindex_doc_ids.json"


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    api_key = PAGEINDEX_API_KEY.strip()
    if not api_key:
        return

    try:
        from pageindex import PageIndexClient

        client = PageIndexClient(api_key=api_key)
        doc_ids = {}
        if DOC_IDS_FILE.exists():
            try:
                doc_ids = json.loads(DOC_IDS_FILE.read_text(encoding="utf-8"))
            except Exception:
                doc_ids = {}

        pdf_files = list(LEGAL_LANDING_DIR.glob("*.pdf"))
        for pdf_path in pdf_files:
            filename = pdf_path.name
            if filename in doc_ids:
                continue
            try:
                response = client.submit_document(file_path=str(pdf_path))
                doc_id = response.get("doc_id") or response.get("id")
                if doc_id:
                    doc_ids[filename] = doc_id
            except Exception:
                pass

        DOC_IDS_FILE.write_text(
            json.dumps(doc_ids, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if not query.strip() or top_k <= 0:
        return []

    api_key = PAGEINDEX_API_KEY.strip()
    if not api_key:
        return []

    doc_ids = {}
    if DOC_IDS_FILE.exists():
        try:
            doc_ids = json.loads(DOC_IDS_FILE.read_text(encoding="utf-8"))
        except Exception:
            doc_ids = {}

    if not doc_ids:
        return []

    try:
        from pageindex import PageIndexClient

        client = PageIndexClient(api_key=api_key)
        results = []
        for doc_name, doc_id in doc_ids.items():
            try:
                submission = client.submit_query(doc_id=doc_id, query=query)
                retrieval_id = submission.get("retrieval_id")
                if not retrieval_id:
                    continue
                res = client.get_retrieval(retrieval_id=retrieval_id)
                nodes = res.get("nodes", []) if isinstance(res, dict) else []
                for index, node in enumerate(nodes):
                    content = node.get("content") or node.get("text") or ""
                    if not content.strip():
                        continue
                    score = float(node.get("score", 1.0 / (index + 1)))
                    results.append({
                        "id": f"pageindex::{doc_id}::{index}",
                        "content": content,
                        "score": score,
                        "metadata": {
                            "source": doc_name,
                            "title": doc_name,
                            "doc_type": "legal",
                            "url": None,
                            "chunk_index": index,
                        },
                        "retrieval_method": "pageindex",
                    })
            except Exception:
                continue

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:top_k]
    except Exception:
        return []


if __name__ == "__main__":
    upload_documents()
