"""Hybrid retrieval (dense + BM25 + RRF) and citation-grounded generation.

Self-contained: builds an in-memory embedding index and a BM25 index over
the legal corpus, so it does not depend on ChromaDB or the src/task*.py
exercises. Suitable for the small (~a few hundred chunk) corpus this
chatbot serves.
"""

import hashlib
import pickle
import re
import threading
from typing import TypedDict

import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer

from . import config
from .corpus import Chunk, load_chunks
from .llm import LLMError, call_llm

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


class SearchResult(TypedDict):
    id: str
    content: str
    score: float
    title: str
    source: str
    retrieval_method: str


_lock = threading.Lock()
_state: dict | None = None


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _fingerprint(chunks: list[Chunk]) -> str:
    digest = hashlib.sha256()
    digest.update(config.EMBEDDING_MODEL.encode("utf-8"))
    for chunk in chunks:
        digest.update(chunk.id.encode("utf-8"))
        digest.update(chunk.content.encode("utf-8"))
    return digest.hexdigest()


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def _build_or_load_embeddings(chunks: list[Chunk], model) -> np.ndarray:
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = config.CACHE_DIR / "embeddings.pkl"
    fingerprint = _fingerprint(chunks)

    if cache_path.exists():
        try:
            with open(cache_path, "rb") as file:
                cached = pickle.load(file)
            if cached.get("fingerprint") == fingerprint:
                return cached["embeddings"]
        except Exception:
            pass

    vectors = np.asarray(
        list(model.embed([chunk.content for chunk in chunks])), dtype=np.float32
    )
    embeddings = _normalize(vectors)
    with open(cache_path, "wb") as file:
        pickle.dump({"fingerprint": fingerprint, "embeddings": embeddings}, file)
    return embeddings


def _get_state() -> dict:
    global _state
    if _state is not None:
        return _state
    with _lock:
        if _state is not None:
            return _state

        chunks = load_chunks()
        if not chunks:
            raise RuntimeError(
                "Không tìm thấy chunk nào trong data/standardized/legal. "
                "Hãy kiểm tra data/landing/legal có tài liệu hợp lệ."
            )

        tokenized_corpus = [_tokenize(chunk.content) for chunk in chunks]
        bm25 = BM25Okapi(tokenized_corpus)

        if config.EMBEDDING_BACKEND == "fastembed":
            from fastembed import TextEmbedding

            model = TextEmbedding(model_name=config.EMBEDDING_MODEL)
            embeddings = _build_or_load_embeddings(chunks, model)
            _state = {
                "backend": "fastembed",
                "chunks": chunks,
                "embeddings": embeddings,
                "model": model,
                "bm25": bm25,
            }
        else:
            # Default backend: TF-IDF cosine similarity (scikit-learn). Pure
            # Python/C, no network call and no torch dependency - see
            # config.EMBEDDING_BACKEND for why this is the default here.
            vectorizer = TfidfVectorizer()
            doc_vectors = vectorizer.fit_transform([chunk.content for chunk in chunks])
            _state = {
                "backend": "tfidf",
                "chunks": chunks,
                "vectorizer": vectorizer,
                "doc_vectors": doc_vectors,
                "bm25": bm25,
            }
        return _state


def warm_up() -> dict:
    """Force index construction; returns basic stats for health checks."""
    state = _get_state()
    return {
        "corpus_chunks": len(state["chunks"]),
        "embedding_backend": state["backend"],
        "embedding_model": config.EMBEDDING_MODEL if state["backend"] == "fastembed" else "tfidf",
        "llm_provider": config.LLM_PROVIDER,
        "llm_model": config.LLM_MODEL or config.DEFAULT_MODELS.get(config.LLM_PROVIDER, ""),
    }


def _to_result(chunk: Chunk, score: float, method: str) -> SearchResult:
    return {
        "id": chunk.id,
        "content": chunk.content,
        "score": float(score),
        "title": chunk.title,
        "source": chunk.source,
        "retrieval_method": method,
    }


def dense_search(query: str, top_k: int = 10) -> list[SearchResult]:
    state = _get_state()
    chunks = state["chunks"]

    if state["backend"] == "fastembed":
        query_vector = np.asarray(next(iter(state["model"].embed([query]))), dtype=np.float32)
        query_vector = query_vector / max(np.linalg.norm(query_vector), 1e-8)
        scores = state["embeddings"] @ query_vector
    else:
        query_vector = state["vectorizer"].transform([query])
        # TfidfVectorizer output rows are L2-normalized by default, so the
        # dot product below is already cosine similarity.
        scores = (state["doc_vectors"] @ query_vector.T).toarray().ravel()

    order = np.argsort(scores)[::-1][:top_k]
    return [_to_result(chunks[i], scores[i], "dense") for i in order]


def lexical_search(query: str, top_k: int = 10) -> list[SearchResult]:
    state = _get_state()
    scores = state["bm25"].get_scores(_tokenize(query))
    order = np.argsort(scores)[::-1][:top_k]
    chunks = state["chunks"]
    return [_to_result(chunks[i], scores[i], "bm25") for i in order if scores[i] > 0]


def rerank_rrf(
    ranked_lists: list[list[SearchResult]], top_k: int = 5, k: int = config.RRF_K
) -> list[SearchResult]:
    scores: dict[str, float] = {}
    items: dict[str, SearchResult] = {}
    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            item_id = item["id"]
            scores[item_id] = scores.get(item_id, 0.0) + 1 / (k + rank)
            items[item_id] = item

    ranked_ids = sorted(scores, key=scores.get, reverse=True)
    results = []
    for item_id in ranked_ids[:top_k]:
        result = dict(items[item_id])
        result["score"] = scores[item_id]
        result["retrieval_method"] = "hybrid"
        results.append(result)
    return results


def retrieve(query: str, top_k: int = config.TOP_K, use_hybrid: bool = True) -> list[SearchResult]:
    dense = dense_search(query, top_k=top_k * 2)
    if not use_hybrid:
        return dense[:top_k]
    sparse = lexical_search(query, top_k=top_k * 2)
    return rerank_rrf([dense, sparse], top_k=top_k)


def reorder_for_llm(chunks: list[SearchResult]) -> list[SearchResult]:
    """Put the strongest chunks at the front and back of the context window."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[SearchResult]) -> str:
    parts = []
    for index, chunk in enumerate(chunks, 1):
        parts.append(
            f"[Nguồn {index} | {chunk['title']} | Tệp: {chunk['source']}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def generate_with_citation(
    query: str, top_k: int = config.TOP_K, use_hybrid: bool = True
) -> dict:
    chunks = retrieve(query, top_k=top_k, use_hybrid=use_hybrid)
    retrieval_method = "hybrid" if use_hybrid else "dense"

    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
            "retrieval_method": retrieval_method,
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Ngữ cảnh:\n{context}\n\nCâu hỏi: {query}"

    try:
        answer = call_llm(config.SYSTEM_PROMPT, user_message)
    except LLMError as error:
        answer = (
            f"(Chưa thể gọi mô hình sinh câu trả lời: {error}. "
            "Dưới đây là các đoạn trích dẫn liên quan nhất tìm được trong "
            "kho dữ liệu để bạn tham khảo trực tiếp.)"
        )

    if not answer.strip():
        answer = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

    return {"answer": answer, "sources": chunks, "retrieval_method": retrieval_method}


if __name__ == "__main__":
    import json

    result = generate_with_citation("Hợp đồng mua bán căn hộ có bắt buộc công chứng không?")
    print(json.dumps({**result, "sources": len(result["sources"])}, ensure_ascii=False, indent=2))
