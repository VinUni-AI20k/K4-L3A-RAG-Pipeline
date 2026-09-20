"""Dense retrieval over the Chroma collection produced by task 4."""

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Return unique dense results, descending by cosine similarity."""
    if top_k <= 0 or not query or not query.strip():
        return []
    response = get_collection().query(
        query_embeddings=[embed_texts([query])[0]], n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    rows = zip(response.get("ids", [[]])[0], response.get("documents", [[]])[0],
               response.get("metadatas", [[]])[0], response.get("distances", [[]])[0])
    results, seen = [], set()
    for item_id, content, metadata, distance in rows:
        if item_id in seen:
            continue
        seen.add(item_id)
        normalized_metadata = dict(metadata or {})
        normalized_metadata["url"] = normalized_metadata.get("url") or None
        results.append({"id": item_id, "content": content,
                        "score": max(0.0, 1.0 - float(distance)),
                        "metadata": normalized_metadata, "retrieval_method": "dense"})
    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]
