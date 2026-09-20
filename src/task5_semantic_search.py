"""
Task 5 — Semantic search.

Embed query bằng chính hàm của Task 4, query ChromaDB và đổi cosine distance
thành similarity. Output phải theo SearchResult, sort giảm dần và không quá top_k.
"""

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần."""
    if top_k <= 0 or not query or not query.strip():
        return []

    collection = get_collection()
    query_vector = embed_texts([query])[0]

    response = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    if not response or not response.get("ids") or not response["ids"][0]:
        return []

    results = []
    seen_ids = set()
    for item_id, content, raw_metadata, distance in zip(
        response["ids"][0],
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0],
    ):
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)

        metadata = dict(raw_metadata) if raw_metadata else {}
        if metadata.get("url") == "":
            metadata["url"] = None

        if "chunk_index" in metadata and not isinstance(metadata["chunk_index"], int):
            try:
                metadata["chunk_index"] = int(metadata["chunk_index"])
            except (ValueError, TypeError):
                metadata["chunk_index"] = 0

        score = float(max(0.0, 1.0 - float(distance)))
        results.append({
            "id": item_id,
            "content": content,
            "score": score,
            "metadata": metadata,
            "retrieval_method": "dense",
        })

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    import io
    import sys

    if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    for result in semantic_search("quy chế tuyển sinh đại học", top_k=3):
        print(f"[{result['score']:.4f}] {result['id']} - {result['metadata'].get('title')}")
