"""
Task 5 — Semantic search.

Embed query bằng chính hàm của Task 4, query ChromaDB và đổi cosine distance
thành similarity. Output phải theo SearchResult, sort giảm dần và không quá top_k.
"""

from .task4_chunking_indexing import embed_texts, get_collection
from .contracts import validate_search_results


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        raise ValueError("top_k must be an integer")
    if top_k <= 0:
        return []

    collection = get_collection()
    count_method = getattr(collection, "count", None)
    collection_size = count_method() if callable(count_method) else top_k
    if collection_size == 0:
        return []

    query_vector = embed_texts([query.strip()])[0]
    response = collection.query(
        query_embeddings=[query_vector],
        n_results=min(top_k, collection_size),
        include=["documents", "metadatas", "distances"],
    )

    results = []
    seen_ids = set()
    for item_id, content, metadata, distance in zip(
        response.get("ids", [[]])[0],
        response.get("documents", [[]])[0],
        response.get("metadatas", [[]])[0],
        response.get("distances", [[]])[0],
    ):
        if item_id in seen_ids or not content or metadata is None:
            continue
        normalized_metadata = dict(metadata)
        if normalized_metadata.get("url") == "":
            normalized_metadata["url"] = None
        results.append(
            {
                "id": item_id,
                "content": content,
                "score": float(1.0 - distance),
                "metadata": normalized_metadata,
                "retrieval_method": "dense",
            }
        )
        seen_ids.add(item_id)

    results.sort(key=lambda item: item["score"], reverse=True)
    results = results[:top_k]
    validate_search_results(results, top_k=top_k, expected_method="dense")
    return results


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for result in semantic_search("test query", top_k=3):
        print(result)
