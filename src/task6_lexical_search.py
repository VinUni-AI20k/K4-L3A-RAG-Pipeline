"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

import re
import unicodedata

from rank_bm25 import BM25Plus


CORPUS: list[dict] = []


def tokenize(text: str) -> list[str]:
    """Tokenize chung cho corpus và query: bỏ dấu + tách từ.

    Bỏ dấu giúp query gõ không dấu ("thue tndn") vẫn khớp với
    "thuế TNDN" trong corpus. Tiếng Việt tách âm tiết bằng khoảng trắng
    nên tokenize theo từng từ là đủ cho BM25.
    """
    normalized = unicodedata.normalize("NFD", text.lower())
    without_marks = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return re.findall(r"\w+", without_marks)


def build_bm25_index(corpus: list[dict]) -> BM25Plus:
    """Tạo BM25 index từ cùng corpus chunks của Task 4.

    Dùng BM25Plus thay vì BM25Okapi vì IDF của Okapi bằng 0 khi từ xuất
    hiện trong ≤ nửa corpus — trên corpus nhỏ mọi score sẽ bằng 0.
    """
    if not corpus:
        raise ValueError("corpus is empty — index Task 4 before searching")
    tokenized = [tokenize(item["content"]) for item in corpus]
    return BM25Plus(tokenized)


def _load_corpus() -> list[dict]:
    """Ưu tiên CORPUS gán thủ công; nếu rỗng thì load từ ChromaDB."""
    if CORPUS:
        return CORPUS
    from .task4_chunking_indexing import get_collection

    data = get_collection().get(include=["documents", "metadatas"])
    return [
        {"id": chunk_id, "content": content, "metadata": metadata}
        for chunk_id, content, metadata in zip(
            data["ids"], data["documents"], data["metadatas"]
        )
    ]


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    import numpy as np

    corpus = _load_corpus()
    if not corpus or top_k <= 0:
        return []

    bm25 = build_bm25_index(corpus)
    scores = bm25.get_scores(tokenize(query))
    indices = np.argsort(scores)[::-1][:top_k]
    results = []
    for index in indices:
        if scores[index] <= 0:
            continue
        item = corpus[index]
        results.append(
            {
                "id": item["id"],
                "content": item["content"],
                "score": float(scores[index]),
                "metadata": item["metadata"],
                "retrieval_method": "bm25",
            }
        )
    return results


if __name__ == "__main__":
    for result in lexical_search("test query", top_k=3):
        print(result)
