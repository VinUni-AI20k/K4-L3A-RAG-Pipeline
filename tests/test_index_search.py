from src import task4_chunking_indexing as indexing
from src import task5_semantic_search as semantic
from src import task6_lexical_search as lexical


def test_index_is_idempotent_and_shared_by_dense_and_bm25(tmp_path, monkeypatch):
    monkeypatch.setattr(indexing, "CHROMA_DIR", tmp_path / "chroma")
    chunks = [
        {
            "id": "legal/rules.md::chunk-0",
            "content": "đăng ký học phần",
            "metadata": {
                "source": "legal/rules.md",
                "title": "Quy chế",
                "doc_type": "legal",
                "url": None,
                "chunk_index": 0,
            },
            "embedding": [1.0, 0.0],
        },
        {
            "id": "news/notice.md::chunk-0",
            "content": "thông báo học phí",
            "metadata": {
                "source": "news/notice.md",
                "title": "Thông báo",
                "doc_type": "news",
                "url": "https://example.test",
                "chunk_index": 0,
            },
            "embedding": [0.0, 1.0],
        },
    ]
    indexing.index_to_vectorstore(chunks)
    indexing.index_to_vectorstore(chunks)
    assert indexing.get_collection().count() == 2

    monkeypatch.setattr(semantic, "get_collection", indexing.get_collection)
    monkeypatch.setattr(semantic, "embed_texts", lambda _texts: [[1.0, 0.0]])
    monkeypatch.setattr(lexical, "get_collection", indexing.get_collection)
    monkeypatch.setattr(lexical, "CORPUS", [])
    assert semantic.semantic_search("đăng ký", 1)[0]["id"] == chunks[0]["id"]
    assert lexical.lexical_search("học phí", 1)[0]["id"] == chunks[1]["id"]

    indexing.index_to_vectorstore(chunks[:1])
    assert indexing.get_collection().count() == 1

def test_vietnamese_bm25_tokenizer_removes_stopwords_and_keeps_phrases():
    tokens = lexical._tokenize("Khi nào sinh viên đăng ký học phần?")
    assert not {"khi", "nào", "sinh", "viên"}.intersection(tokens)
    assert {"đăng_ký", "học_phần", "đăng_ký_học"} <= set(tokens)
    assert tokens.count("đăng_ký_học") == 2


def test_chunking_keeps_the_equivalent_course_definition_together():
    chunks = indexing.chunk_documents(indexing.load_documents())
    assert any(
        "Hai học phần được coi là tương đương" in chunk["content"]
        and "thiểu 70%" in chunk["content"]
        for chunk in chunks
    )
