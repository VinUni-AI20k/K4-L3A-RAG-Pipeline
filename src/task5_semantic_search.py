"""
Task 5 — Semantic search.

Embed query bằng chính hàm của Task 4, query ChromaDB và đổi cosine distance
thành similarity. Output phải theo SearchResult, sort giảm dần và không quá top_k.
"""

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần."""
    if top_k <= 0 or not query.strip():
        return []
    collection = get_collection()
    count = collection.count() if hasattr(collection, "count") else top_k
    if not count:
        return []
    query_vector = embed_texts([query])[0]
    response = collection.query(
        query_embeddings=[query_vector], n_results=min(top_k, count),
        include=["documents", "metadatas", "distances"],
    )
    results = {}
    for item_id, content, metadata, distance in zip(
        response["ids"][0], response["documents"][0],
        response["metadatas"][0], response["distances"][0],
    ):
        score = max(-1.0, min(1.0, 1.0 - float(distance)))
        if item_id not in results or score > results[item_id]["score"]:
            results[item_id] = {
                "id": item_id, "content": content, "score": score,
                "metadata": {"url": None, **(metadata or {})},
                "retrieval_method": "dense",
            }
    return sorted(results.values(), key=lambda item: item["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    for result in semantic_search("test query", top_k=3):
        print(result)
