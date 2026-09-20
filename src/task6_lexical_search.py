"""Unicode-aware BM25 retrieval over the exact corpus stored in ChromaDB."""

from __future__ import annotations

import re

from .task4_chunking_indexing import get_collection


CORPUS: list[dict] = []
_TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)
_CACHE_SIGNATURE: tuple[tuple[str, str], ...] | None = None
_CACHED_INDEX = None


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.casefold())


def _restore_metadata(metadata: dict | None) -> dict:
    output = dict(metadata or {})
    if output.get("url") == "":
        output["url"] = None
    return output


def _load_corpus_from_chroma() -> list[dict]:
    response = get_collection().get(include=["documents", "metadatas"])
    ids = response.get("ids") or []
    documents = response.get("documents") or []
    metadatas = response.get("metadatas") or []
    return [
        {"id": item_id, "content": content, "metadata": _restore_metadata(metadata)}
        for item_id, content, metadata in zip(ids, documents, metadatas)
    ]


def _current_corpus() -> list[dict]:
    # CORPUS remains injectable for tests. Normally it is loaded from Chroma,
    # guaranteeing identical IDs/content for the dense and lexical branches.
    global CORPUS
    if not CORPUS:
        CORPUS = _load_corpus_from_chroma()
    return CORPUS


def build_bm25_index(corpus: list[dict]):
    """Build a BM25Okapi index using Unicode-aware tokenization."""
    from rank_bm25 import BM25Okapi

    return BM25Okapi([_tokenize(item["content"]) for item in corpus])


def _index_for(corpus: list[dict]):
    global _CACHE_SIGNATURE, _CACHED_INDEX
    signature = tuple((str(item["id"]), str(item["content"])) for item in corpus)
    if signature != _CACHE_SIGNATURE:
        _CACHED_INDEX = build_bm25_index(corpus)
        _CACHE_SIGNATURE = signature
    return _CACHED_INDEX


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Return unique BM25 results ordered by decreasing score."""
    query_tokens = _tokenize(query) if isinstance(query, str) else []
    if top_k <= 0 or not query_tokens:
        return []
    corpus = _current_corpus()
    if not corpus:
        return []

    scores = _index_for(corpus).get_scores(query_tokens)
    query_set = set(query_tokens)
    ranked: list[tuple[float, int, int]] = []
    for index, (item, raw_score) in enumerate(zip(corpus, scores)):
        overlap = len(query_set.intersection(_tokenize(item["content"])))
        ranked.append((float(raw_score), overlap, index))

    has_positive = any(score > 0 for score, _, _ in ranked)
    if has_positive:
        ranked = [row for row in ranked if row[0] > 0]
    else:
        # BM25Okapi can return exactly zero for a real match in tiny corpora
        # (N=2, document frequency=1). Keep lexical matches in that edge case.
        ranked = [row for row in ranked if row[1] > 0]
    ranked.sort(key=lambda row: (-row[0], -row[1], row[2]))

    results: list[dict] = []
    seen: set[str] = set()
    for score, _, index in ranked:
        item = corpus[index]
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        results.append(
            {
                "id": item["id"],
                "content": item["content"],
                "score": score,
                "metadata": dict(item["metadata"]),
                "retrieval_method": "bm25",
            }
        )
        if len(results) >= top_k:
            break
    return results


if __name__ == "__main__":
    for result in lexical_search("Luật Du lịch", top_k=3):
        print(result)
