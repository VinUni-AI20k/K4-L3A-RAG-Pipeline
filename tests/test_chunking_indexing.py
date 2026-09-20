from src import task4_chunking_indexing as task


def test_load_documents_reads_source_metadata():
    documents = task.load_documents()
    assert len(documents) == 8
    news = next(item for item in documents if item["id"] == "news/article_01.md")
    assert news["metadata"]["url"].startswith("https://")
    assert news["metadata"]["doc_type"] == "news"
    legal = next(item for item in documents if item["id"] == "legal/10.md")
    assert legal["metadata"]["title"].startswith("Vật lí 10")


def test_embed_chunks_uses_shared_embedder(monkeypatch):
    monkeypatch.setattr(task, "embed_texts", lambda texts: [[float(len(text))] for text in texts])
    chunks = [{"id": "one", "content": "abc", "metadata": {"chunk_index": 0}}]
    result = task.embed_chunks(chunks)
    assert result[0]["embedding"] == [3.0]
    assert "embedding" not in chunks[0]


def test_index_upserts_and_removes_stale_ids(monkeypatch):
    class Collection:
        def __init__(self):
            self.ids = {"old"}

        def upsert(self, **kwargs):
            assert kwargs["metadatas"][0]["url"] == ""
            self.ids.update(kwargs["ids"])

        def get(self, **kwargs):
            return {"ids": sorted(self.ids)}

        def delete(self, *, ids):
            self.ids.difference_update(ids)

    collection = Collection()
    monkeypatch.setattr(task, "get_collection", lambda: collection)
    task.index_to_vectorstore(
        [{
            "id": "new",
            "content": "text",
            "embedding": [0.1, 0.2],
            "metadata": {
                "source": "source.md",
                "title": "Title",
                "doc_type": "legal",
                "url": None,
                "chunk_index": 0,
            },
        }]
    )
    assert collection.ids == {"new"}
