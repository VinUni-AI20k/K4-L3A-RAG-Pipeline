"""Vectorless fallback over document chunks.

The local implementation is deliberately provider-independent and remains usable
when the optional PageIndex service is unavailable.
"""
import re
from .task4_chunking_indexing import chunk_documents, load_documents

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)

def upload_documents() -> None:
    """Compatibility hook: the local fallback needs no remote upload."""
    documents = load_documents()
    print(f"Vectorless fallback ready for {len(documents)} documents")

def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    if not query.strip() or top_k <= 0:
        return []
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    chunks = chunk_documents(load_documents())
    if not chunks:
        return []
    texts = [item["content"] for item in chunks]
    matrix = TfidfVectorizer(lowercase=True, token_pattern=r"(?u)\b\w+\b",
        ngram_range=(1, 2), sublinear_tf=True).fit_transform(texts + [query])
    scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    indices = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), chunks[i]["id"]))
    results = []
    for index in indices[:top_k]:
        if scores[index] <= 0:
            continue
        item = chunks[index]
        results.append({"id": item["id"], "content": item["content"],
            "score": float(scores[index]), "metadata": dict(item["metadata"]),
            "retrieval_method": "pageindex"})
    return results

if __name__ == "__main__":
    upload_documents()
