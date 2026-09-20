"""BM25 lexical retrieval over the same chunks used by dense retrieval."""

import math
import re
from collections import Counter

CORPUS: list[dict] = []


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def build_bm25_index(corpus: list[dict]):
    """Build BM25, with a small compatible fallback for minimal environments."""
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        return _FallbackBM25([_tokens(item["content"]) for item in corpus])
    return BM25Okapi([_tokens(item["content"]) for item in corpus])


class _FallbackBM25:
    """Dependency-free BM25Okapi subset used when rank-bm25 is unavailable."""

    def __init__(self, tokenized_corpus: list[list[str]]) -> None:
        self.documents = [Counter(tokens) for tokens in tokenized_corpus]
        self.lengths = [len(tokens) for tokens in tokenized_corpus]
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 0
        self.document_frequency = Counter(
            term for document in self.documents for term in document
        )

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        total = len(self.documents)
        scores: list[float] = []
        for document, length in zip(self.documents, self.lengths):
            score = 0.0
            for term in query_tokens:
                frequency = document.get(term, 0)
                if not frequency:
                    continue
                inverse_frequency = math.log(
                    1 + (total - self.document_frequency[term] + 0.5)
                    / (self.document_frequency[term] + 0.5)
                )
                denominator = frequency + 1.5 * (1 - 0.75 + 0.75 * length / self.average_length)
                score += inverse_frequency * frequency * 2.5 / denominator
            scores.append(score)
        return scores


def _corpus() -> list[dict]:
    if CORPUS:
        return CORPUS
    from .task4_chunking_indexing import chunk_documents, load_documents
    return chunk_documents(load_documents())


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Return positive-score BM25 SearchResults in descending score order."""
    if top_k <= 0 or not query or not query.strip():
        return []
    corpus = _corpus()
    if not corpus:
        return []
    scores = build_bm25_index(corpus).get_scores(_tokens(query))
    ranked = sorted(enumerate(scores), key=lambda pair: float(pair[1]), reverse=True)
    results = []
    for index, score in ranked:
        if float(score) <= 0 or len(results) >= top_k:
            continue
        item = corpus[index]
        results.append({"id": item["id"], "content": item["content"], "score": float(score),
                        "metadata": dict(item["metadata"]), "retrieval_method": "bm25"})
    return results
