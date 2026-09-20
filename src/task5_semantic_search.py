"""Dense retrieval over the Task 4 Chroma collection."""

from .task4_chunking_indexing import embed_texts, get_collection


def _python_metadata(metadata: dict | None) -> dict:
    output = dict(metadata or {})
    if output.get("url") == "":
        output["url"] = None
    return output


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Return unique dense results ordered by cosine similarity."""
    if top_k <= 0 or not isinstance(query, str) or not query.strip():
        return []

    collection = get_collection()
    try:
        collection_size = collection.count()
    except (AttributeError, TypeError):
        # Contract-test fakes need not implement the full Chroma interface.
        collection_size = top_k
    if collection_size <= 0:
        return []

    response = collection.query(
        query_embeddings=embed_texts([query.strip()]),
        n_results=min(top_k, collection_size),
        include=["documents", "metadatas", "distances"],
    )
    rows = zip(
        (response.get("ids") or [[]])[0],
        (response.get("documents") or [[]])[0],
        (response.get("metadatas") or [[]])[0],
        (response.get("distances") or [[]])[0],
    )
    by_id: dict[str, dict] = {}
    for item_id, content, metadata, distance in rows:
        result = {
            "id": item_id,
            "content": content,
            "score": 1.0 - float(distance),
            "metadata": _python_metadata(metadata),
            "retrieval_method": "dense",
        }
        previous = by_id.get(item_id)
        if previous is None or result["score"] > previous["score"]:
            by_id[item_id] = result
    return sorted(by_id.values(), key=lambda item: item["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    for result in semantic_search("du lịch Việt Nam", top_k=3):
        print(result)
