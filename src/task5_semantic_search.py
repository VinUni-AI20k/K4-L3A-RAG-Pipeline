"""Task 5: dense semantic search over the Task 4 Chroma collection."""

from .contracts import validate_search_results
from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Return unique dense results ordered by raw cosine similarity.

    Task 4 creates the collection with cosine distance, so Chroma's returned
    distance is converted with ``similarity = 1 - distance``. The value is not
    clipped because Task 9 must compare its fallback threshold against the
    original cosine score.
    """
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        raise TypeError("top_k must be an integer")
    query = query.strip()
    if not query or top_k <= 0:
        return []

    query_embeddings = embed_texts([query])
    if len(query_embeddings) != 1 or not query_embeddings[0]:
        raise ValueError("Embedding provider must return one non-empty query vector")

    response = get_collection().query(
        query_embeddings=[query_embeddings[0]],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    keys = ("ids", "documents", "metadatas", "distances")
    rows: dict[str, list] = {}
    for key in keys:
        batches = response.get(key)
        if not isinstance(batches, list) or not batches:
            rows[key] = []
        elif not isinstance(batches[0], list):
            raise ValueError(f"Chroma response field {key!r} has an invalid shape")
        else:
            rows[key] = batches[0]

    lengths = {len(row) for row in rows.values()}
    if len(lengths) > 1:
        raise ValueError("Chroma response fields have inconsistent lengths")

    # Chroma normally returns unique IDs. Keeping the highest similarity here
    # also enforces the public contract if a custom backend returns duplicates.
    by_id: dict[str, dict] = {}
    for item_id, content, metadata, distance in zip(
        rows["ids"],
        rows["documents"],
        rows["metadatas"],
        rows["distances"],
    ):
        try:
            score = 1.0 - float(distance)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid cosine distance for result {item_id!r}") from exc
        result = {
            "id": item_id,
            "content": content,
            "score": score,
            "metadata": metadata,
            "retrieval_method": "dense",
        }
        existing = by_id.get(item_id)
        if existing is None or score > existing["score"]:
            by_id[item_id] = result

    results = sorted(by_id.values(), key=lambda item: (-item["score"], item["id"]))[:top_k]
    validate_search_results(results, top_k=top_k, expected_method="dense")
    return results


if __name__ == "__main__":
    for result in semantic_search("Điều kiện kinh doanh dịch vụ lữ hành", top_k=3):
        print(result)
