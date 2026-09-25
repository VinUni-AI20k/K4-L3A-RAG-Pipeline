"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.

Tokenizer: tiếng Việt viết theo âm tiết ("hoàn tiền" = 2 âm tiết), nên index cả
unigram âm tiết và bigram âm tiết liền kề để BM25 bắt được từ ghép.
"""

import math
import re
import unicodedata

from rank_bm25 import BM25Okapi


# Rỗng = tự nạp chunks từ ChromaDB (cùng corpus của Task 4) ở lần gọi đầu.
CORPUS: list[dict] = []

_INDEX_CACHE: dict = {}


class LuceneIdfBM25(BM25Okapi):
    """BM25Okapi với IDF kiểu Lucene: log(1 + (N - n + 0.5) / (n + 0.5)).

    IDF gốc của BM25Okapi bằng 0 hoặc âm khi term xuất hiện trong >= nửa số
    chunks, làm các term phổ biến (vd. "shopee") triệt tiêu điểm. Công thức
    Lucene luôn dương.
    """

    def _calc_idf(self, nd):
        for word, freq in nd.items():
            self.idf[word] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))


def tokenize(text: str) -> list[str]:
    syllables = re.findall(r"\w+", unicodedata.normalize("NFC", text).lower())
    bigrams = [f"{a}_{b}" for a, b in zip(syllables, syllables[1:])]
    return syllables + bigrams


def load_corpus() -> list[dict]:
    """Đọc toàn bộ chunks đã index trong ChromaDB."""
    from .task4_chunking_indexing import get_collection

    data = get_collection().get(include=["documents", "metadatas"])
    corpus = [
        {"id": item_id, "content": content, "metadata": {"url": None, **dict(metadata)}}
        for item_id, content, metadata in zip(data["ids"], data["documents"], data["metadatas"])
    ]
    return sorted(corpus, key=lambda item: item["id"])


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    return LuceneIdfBM25([tokenize(item["content"]) for item in corpus])


def _get_index(corpus: list[dict]):
    key = (id(corpus), len(corpus))
    if _INDEX_CACHE.get("key") != key:
        _INDEX_CACHE["key"] = key
        _INDEX_CACHE["bm25"] = build_bm25_index(corpus)
    return _INDEX_CACHE["bm25"]


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    global CORPUS
    if not CORPUS:
        CORPUS = load_corpus()
    corpus = CORPUS
    query_tokens = tokenize(query)
    if not corpus or not query_tokens or top_k <= 0:
        return []

    scores = _get_index(corpus).get_scores(query_tokens)
    ranked = sorted(range(len(corpus)), key=lambda index: scores[index], reverse=True)
    results = []
    for index in ranked[:top_k]:
        if scores[index] <= 0:
            break
        item = corpus[index]
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": float(scores[index]),
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })
    return results


if __name__ == "__main__":
    for result in lexical_search("phí hoàn trả SPX Express", top_k=3):
        print(f"{result['score']:.3f} {result['id']}")
