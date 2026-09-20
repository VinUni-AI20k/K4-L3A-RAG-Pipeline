"""Semantic search using the same Gemini embedding model as indexing."""
from .task4_chunking_indexing import embed_texts, get_collection

def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    if not query.strip() or top_k <= 0:
        return []
    query_vector = embed_texts([query])[0]
    collection = get_collection()
    raw = collection.query(query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"])
    results = [{"id": item_id, "content": content,
        "score": float(1.0 - distance), "metadata": metadata,
        "retrieval_method": "dense"}
        for item_id, content, metadata, distance in zip(raw["ids"][0],
            raw["documents"][0], raw["metadatas"][0], raw["distances"][0])]
    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]

if __name__ == "__main__":
    print(semantic_search("Du lịch Hà Giang mùa nào đẹp?", 3))
