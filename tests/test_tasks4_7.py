"""Offline checks for tasks 4–7; no model downloads or provider requests."""

from copy import deepcopy
from types import SimpleNamespace
import sys
import unicodedata

import numpy as np
import pytest

from src import task4_chunking_indexing as indexing
from src import task5_semantic_search as semantic
from src import task6_lexical_search as lexical
from src import task7_reranking as fusion
from src.contracts import validate_document, validate_search_results


def document(item_id="legal/policy.md", content="Tuition policy"):
    return {
        "id": item_id, "content": content,
        "metadata": {"source": item_id, "title": "Policy", "doc_type": "legal", "url": None},
    }


def test_load_and_chunk_preserve_sources(tmp_path, monkeypatch):
    monkeypatch.setattr(indexing, "STANDARDIZED_DIR", tmp_path)
    for folder in ("legal", "news"):
        (tmp_path / folder).mkdir()
    (tmp_path / "legal/policy.md").write_text("# Policy\n" + "Tuition. " * 200, encoding="utf-8")
    (tmp_path / "news/article.md").write_text(
        "# Announcement\n\n**Source:** https://example.com/article\n\nNews content", encoding="utf-8",
    )
    (tmp_path / "news/empty.md").write_text("  ", encoding="utf-8")
    documents = indexing.load_documents()
    assert len(documents) == 2
    assert documents[1]["metadata"]["url"] == "https://example.com/article"
    assert documents[1]["metadata"]["title"] == "Announcement"
    chunks = indexing.chunk_documents(documents)
    assert chunks == indexing.chunk_documents(documents)
    for chunk in chunks:
        validate_document(chunk, require_chunk=True)
        assert len(chunk["content"]) <= indexing.CHUNK_SIZE


def test_embedding_batches_do_not_mutate_chunks(monkeypatch):
    monkeypatch.setattr(indexing, "EMBEDDING_BATCH_SIZE", 2)
    calls = []

    def embed(texts):
        calls.append(texts)
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(indexing, "embed_texts", embed)
    chunks = indexing.chunk_documents([document(str(i)) for i in range(5)])
    original = deepcopy(chunks)
    output = indexing.embed_chunks(chunks)
    assert chunks == original
    assert [len(batch) for batch in calls] == [2, 2, 1]
    assert len(output) == 5
    monkeypatch.setattr(indexing, "embed_texts", lambda texts: [])
    with pytest.raises(ValueError, match="count"):
        indexing.embed_chunks(chunks)


def test_local_embedding_cache_and_dimension(monkeypatch):
    loaded = []

    class FakeModel:
        def __init__(self, name):
            loaded.append(name)

        def encode(self, texts, **kwargs):
            return np.array([[1.0, 0.0] for _ in texts])

    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=FakeModel))
    monkeypatch.setattr(indexing, "EMBEDDING_PROVIDER", "sentence_transformers")
    monkeypatch.setattr(indexing, "EMBEDDING_MODEL", "offline-test")
    monkeypatch.setattr(indexing, "EMBEDDING_DIM", 2)
    indexing._local_model.cache_clear()
    try:
        assert indexing.embed_texts([]) == []
        assert indexing.embed_texts(["document"]) == [[1.0, 0.0]]
        indexing.embed_texts(["query"])
        assert loaded == ["offline-test"]
        monkeypatch.setattr(indexing, "EMBEDDING_DIM", 3)
        with pytest.raises(ValueError, match="dimension"):
            indexing.embed_texts(["query"])
    finally:
        indexing._local_model.cache_clear()


def test_chroma_roundtrip_shared_corpus_and_cosine(tmp_path, monkeypatch):
    monkeypatch.setattr(indexing, "CHROMA_DIR", tmp_path / "chroma")
    monkeypatch.setattr(indexing, "EMBEDDING_DIM", 2)
    monkeypatch.setattr(indexing, "EMBEDDING_PROVIDER", "sentence_transformers")
    monkeypatch.setattr(indexing, "EMBEDDING_MODEL", "offline-vectors")
    chunks = indexing.chunk_documents([
        document("legal/tuition.md", "Học phí học kỳ"),
        document("legal/library.md", "Thư viện mở cửa"),
    ])
    embedded = [{**chunk, "embedding": vector} for chunk, vector in zip(chunks, [[1., 0.], [-1., 0.]])]
    indexing.index_to_vectorstore(embedded)
    indexing.index_to_vectorstore(embedded)
    collection = indexing.get_collection()
    assert collection.count() == 2
    monkeypatch.setattr(semantic, "get_collection", indexing.get_collection)
    monkeypatch.setattr(semantic, "embed_texts", lambda texts: [[1., 0.]])
    monkeypatch.setattr(lexical, "get_collection", indexing.get_collection)
    monkeypatch.setattr(lexical, "CORPUS", [])
    dense = semantic.semantic_search("học phí", top_k=10)
    sparse = lexical.lexical_search(unicodedata.normalize("NFD", "HỌC PHÍ!"), top_k=10)
    validate_search_results(dense, top_k=10, expected_method="dense")
    validate_search_results(sparse, top_k=10, expected_method="bm25")
    assert dense[0]["id"] == sparse[0]["id"] == chunks[0]["id"]
    assert dense[0]["score"] == pytest.approx(1.)
    assert dense[1]["score"] == pytest.approx(-1.)
    assert dense[0]["metadata"]["url"] is None
    assert lexical.lexical_search("xyzunknown") == []
    assert indexing.get_collection().count() == 2
    monkeypatch.setattr(indexing, "EMBEDDING_MODEL", "different-model")
    with pytest.raises(ValueError, match="different embedding settings"):
        indexing.get_collection()


def test_empty_queries_and_corpus_do_not_embed(monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Embedding/collection access was not needed")

    monkeypatch.setattr(semantic, "embed_texts", unexpected)
    monkeypatch.setattr(semantic, "get_collection", unexpected)
    monkeypatch.setattr(lexical, "get_collection", unexpected)
    for search in (semantic.semantic_search, lexical.lexical_search):
        assert search(" ") == []
        assert search("query", top_k=0) == []
        assert search("query", top_k=-1) == []
    monkeypatch.setattr(semantic, "get_collection", lambda: SimpleNamespace(count=lambda: 0))
    assert semantic.semantic_search("query") == []
    assert lexical.build_bm25_index([]) is None
    assert lexical.build_bm25_index([document(content="!!!")]) is None


def test_bm25_single_document_and_cache_refresh(monkeypatch):
    chunk = indexing.chunk_documents([document(content="Học phí")])[0]
    monkeypatch.setattr(lexical, "CORPUS", [chunk])
    assert lexical.lexical_search("PHÍ!")[0]["score"] > 0
    chunk["content"] = "library"
    assert lexical.lexical_search("phí") == []
    assert lexical.lexical_search("library")


def test_rrf_deduplicates_without_mutation():
    first = {**indexing.chunk_documents([document()])[0], "score": 0.9, "retrieval_method": "dense"}
    second = {**first, "id": "other", "score": 1.0, "retrieval_method": "bm25"}
    lists = [[first, first, second], [second, first]]
    original = deepcopy(lists)
    results = fusion.rerank_rrf(lists, top_k=10)
    assert lists == original
    validate_search_results(results, top_k=10, expected_method="hybrid")
    assert len(results) == 2
    assert all(item["score"] == pytest.approx(1 / 61 + 1 / 62) for item in results)
    assert fusion.rerank_rrf([], top_k=5) == []
    assert fusion.rerank_rrf(lists, top_k=0) == []
    with pytest.raises(ValueError):
        fusion.rerank_rrf(lists, k=-1)
    with pytest.raises(ValueError, match="already be fused"):
        fusion.rerank_rrf([results])
