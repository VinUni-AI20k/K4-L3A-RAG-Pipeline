"""
Task 5 — Semantic search.

Embed query bằng chính hàm của Task 4, query ChromaDB và đổi cosine distance
thành similarity. Output phải theo SearchResult, sort giảm dần và không quá top_k.
"""

import sys

try:
    from .task4_chunking_indexing import (
        EMBEDDING_MODEL,
        embed_texts,
        get_collection,
    )
except ImportError:  # Hỗ trợ chạy trực tiếp: python src/task5_semantic_search.py
    from task4_chunking_indexing import (
        EMBEDDING_MODEL,
        embed_texts,
        get_collection,
    )


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần."""
    # TODO: Implement semantic search.
    #
    query_vector = embed_texts([query])[0]
    response = get_collection().query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    results = []
    for item_id, content, metadata, distance in zip(
        response["ids"][0],
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0],
    ):
        results.append({
            "id": item_id,
            "content": content,
            "score": max(0.0, 1.0 - distance),
            "metadata": metadata,
            "retrieval_method": "dense",
        })
    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]



if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if EMBEDDING_MODEL.casefold() == "bm25":
        try:
            from .task6_lexical_search import lexical_search
        except ImportError:
            from task6_lexical_search import lexical_search

        print("BM25 mode is active; running lexical search (no model download).")
        results = lexical_search("học phí tuyển sinh", top_k=3)
    else:
        results = semantic_search("học phí tuyển sinh", top_k=3)

    for result in results:
        print(result)
