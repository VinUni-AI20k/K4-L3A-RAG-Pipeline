"""
Task 5 — Semantic search.

Embed query bằng chính hàm của Task 4, query ChromaDB và đổi cosine distance
thành similarity. Output phải theo SearchResult, sort giảm dần và không quá top_k.
"""

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần."""
    if not query.strip() or top_k <= 0:
        return []

    collection = get_collection()
    query_vectors = embed_texts([query])
    if not query_vectors:
        return []
    query_vector = query_vectors[0]

    count_fn = getattr(collection, "count", None)
    if callable(count_fn):
        total_items = count_fn()
        if total_items == 0:
            return []
        n_results = min(top_k, total_items)
    else:
        n_results = top_k

    response = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    if not response.get("ids") or not response["ids"][0]:
        return []

    results = []
    ids = response["ids"][0]
    documents = response.get("documents", [[]])[0]
    metadatas = response.get("metadatas", [[]])[0]
    distances = response.get("distances", [[]])[0]

    for item_id, content, metadata, distance in zip(ids, documents, metadatas, distances):
        # ChromaDB dùng cosine distance [0, 2]; similarity = max(0.0, 1.0 - distance)
        similarity = max(0.0, 1.0 - float(distance))
        results.append({
            "id": item_id,
            "content": content,
            "score": similarity,
            "metadata": metadata if metadata is not None else {},
            "retrieval_method": "dense",
        })

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    for result in semantic_search("quy định về đào tạo lái xe", top_k=3):
        print(result)

