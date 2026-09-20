"""Task 5 ? Semantic search.

Embed query b?ng ch?nh h?m c?a Task 4, query ChromaDB v? ??i cosine distance
th?nh similarity. Output ph?i theo SearchResult, sort gi?m d?n v? kh?ng qu? top_k.
"""

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Tr? v? dense SearchResult theo score gi?m d?n."""
    if top_k <= 0:
        return []

    collection = get_collection()

    # H? tr? fake collection trong contract test (kh?ng c? .count()).
    try:
        count = int(getattr(collection, "count")())
    except Exception:
        count = top_k

    if count <= 0:
        return []

    query_vector = embed_texts([query])[0]
    response = collection.query(
        query_embeddings=[query_vector],
        n_results=min(top_k, count),
        include=["documents", "metadatas", "distances"],
    )

    results = []
    ids = response.get("ids", [[]])[0]
    documents = response.get("documents", [[]])[0]
    metadatas = response.get("metadatas", [[]])[0]
    distances = response.get("distances", [[]])[0]

    for item_id, item_content, metadata, distance in zip(
        ids, documents, metadatas, distances
    ):
        results.append(
            {
                "id": item_id,
                "content": item_content,
                "score": max(0.0, 1.0 - float(distance)),
                "metadata": metadata,
                "retrieval_method": "dense",
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    for result in semantic_search("V?nh H? Long", top_k=3):
        print(result["score"], result["metadata"]["title"])
