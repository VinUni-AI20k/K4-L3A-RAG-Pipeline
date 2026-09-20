"""
Task 5 — Semantic search.

Embed query bằng chính hàm của Task 4, query ChromaDB và đổi cosine distance
thành similarity. Output phải theo SearchResult, sort giảm dần và không quá top_k.
"""

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần."""
    if not query or not query.strip():
        return []

    query_vector = embed_texts([query])[0]
    collection = get_collection()
    response = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    results = []
    if response and response.get("ids") and response["ids"][0]:
        for item_id, content, metadata, distance in zip(
            response["ids"][0],
            response["documents"][0],
            response["metadatas"][0],
            response["distances"][0],
        ):
            # ChromaDB cosine distance: distance = 1 - cosine_similarity
            # Chuyển về similarity score: 1.0 - distance
            score = max(0.0, 1.0 - float(distance))
            results.append({
                "id": item_id,
                "content": content,
                "score": score,
                "metadata": metadata,
                "retrieval_method": "dense",
            })

    # Đảm bảo sắp xếp giảm dần theo score và không vượt quá top_k
    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    test_query = "VAMC xử lý nợ xấu như thế nào"
    print(f"=== Semantic search: '{test_query}' ===")
    for res in semantic_search(test_query, top_k=3):
        print(f"- [{res['score']:.4f}] {res['id']}: {res['content'][:100]}...")
