"""Task 6: lexical retrieval with BM25 over the Task 4 chunks."""

from __future__ import annotations

import math
import re
from collections import Counter

from .contracts import validate_document, validate_search_results
from .task4_chunking_indexing import chunk_documents, load_documents


# ``None`` distinguishes "not loaded yet" from an intentionally empty corpus.
# Tests and applications may replace this with their own contract-compatible
# chunk list before calling ``lexical_search``.
CORPUS: list[dict] | None = None

_TOKEN_PATTERN = re.compile(r"\w+(?:[-/]\w+)*", flags=re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Tokenize Unicode text while preserving legal codes joined by '-' or '/'."""
    return _TOKEN_PATTERN.findall(text.casefold())


def _get_corpus() -> list[dict]:
    global CORPUS
    if CORPUS is None:
        CORPUS = chunk_documents(load_documents())
    return CORPUS


class _EmptyBM25:
    """Small null object keeping the same interface as ``BM25Okapi``."""

    @staticmethod
    def get_scores(query_tokens: list[str]) -> list[float]:
        return []


def build_bm25_index(corpus: list[dict]):
    """Build a BM25 index from contract-compatible Task 4 chunks."""
    if not isinstance(corpus, list):
        raise TypeError("corpus must be a list")
    for item in corpus:
        validate_document(item, require_chunk=True)
    if not corpus:
        return _EmptyBM25()

    try:
        from rank_bm25 import BM25Okapi
    except ImportError as exc:  # pragma: no cover - depends on local setup
        raise RuntimeError("rank-bm25 is required for lexical search") from exc

    tokenized_corpus = [_tokenize(item["content"]) for item in corpus]
    index = BM25Okapi(tokenized_corpus)

    # BM25Okapi's original Robertson IDF is exactly zero when a term appears
    # in half of a tiny corpus. The +1 variant remains positive and is commonly
    # used by search engines, while retaining BM25's length/TF normalization.
    document_count = len(tokenized_corpus)
    document_frequency = Counter(
        token for document in tokenized_corpus for token in set(document)
    )
    index.idf = {
        token: math.log(
            1.0 + (document_count - frequency + 0.5) / (frequency + 0.5)
        )
        for token, frequency in document_frequency.items()
    }
    return index


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Return unique BM25 results ordered by descending lexical score."""
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        raise TypeError("top_k must be an integer")
    query_tokens = _tokenize(query)
    if not query_tokens or top_k <= 0:
        return []

    corpus = _get_corpus()
    if not corpus:
        return []
    index = build_bm25_index(corpus)
    scores = index.get_scores(query_tokens)
    if len(scores) != len(corpus):
        raise ValueError("BM25 returned a score count different from the corpus size")

    # Duplicate IDs should not exist after Task 4. Deduplicating here still
    # guarantees Task 6's public contract for a caller-provided corpus.
    by_id: dict[str, dict] = {}
    for item, raw_score in zip(corpus, scores):
        score = float(raw_score)
        if not math.isfinite(score) or score <= 0.0:
            continue
        result = {
            "id": item["id"],
            "content": item["content"],
            "score": score,
            "metadata": dict(item["metadata"]),
            "retrieval_method": "bm25",
        }
        existing = by_id.get(item["id"])
        if existing is None or score > existing["score"]:
            by_id[item["id"]] = result

    results = sorted(by_id.values(), key=lambda item: (-item["score"], item["id"]))[:top_k]
    validate_search_results(results, top_k=top_k, expected_method="bm25")
    return results


if __name__ == "__main__":
    for result in lexical_search("Luật Du lịch 09/2017/QH14", top_k=3):
        print(result)
