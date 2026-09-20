"""Vietnamese-friendly BM25 over the same chunks as dense retrieval."""
import re
from .task4_chunking_indexing import chunk_documents, load_documents

CORPUS: list[dict] = []
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)

def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.casefold())

def build_bm25_index(corpus: list[dict]):
    from rank_bm25 import BM25Okapi
    return BM25Okapi([_tokens(item["content"]) for item in corpus])

def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    global CORPUS
    if not query.strip() or top_k <= 0:
        return []
    if not CORPUS:
        CORPUS = chunk_documents(load_documents())
    if not CORPUS:
        return []
    scores = build_bm25_index(CORPUS).get_scores(_tokens(query))
    indices = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), CORPUS[i]["id"]))
    results = []
    for index in indices[:top_k]:
        item = CORPUS[index]
        results.append({"id": item["id"], "content": item["content"],
            "score": float(scores[index]), "metadata": dict(item["metadata"]),
            "retrieval_method": "bm25"})
    return results
