import pytest

from src.contracts import validate_search_results
from src import task8_pageindex_vectorless as pageindex


def test_pageindex_returns_empty_without_key(monkeypatch):
    monkeypatch.setattr(pageindex, "_api_key", lambda: "")
    assert pageindex.pageindex_search("động năng") == []
    with pytest.raises(RuntimeError, match="PAGEINDEX_API_KEY"):
        pageindex.upload_documents()


def test_pageindex_parses_retrieved_content(monkeypatch):
    monkeypatch.setattr(pageindex, "_api_key", lambda: "test-key")
    monkeypatch.setattr(pageindex, "_read_cache", lambda: {
        "legal/10.md": {"doc_id": "pi-doc", "sha256": "abc"}
    })
    monkeypatch.setattr(pageindex, "_preferred_sources", lambda query, available: ["legal/10.md"])
    monkeypatch.setattr(pageindex, "load_documents", lambda: [{
        "id": "legal/10.md",
        "metadata": {
            "source": "10.md", "title": "Vật lí 10", "doc_type": "legal", "url": None,
        },
    }])

    def fake_request(method, endpoint, api_key, **kwargs):
        assert api_key == "test-key"
        if endpoint == "/doc/pi-doc/":
            return {"status": "completed", "retrieval_ready": True}
        if endpoint == "/retrieval/":
            assert kwargs["json"]["query"] == "động năng"
            return {"retrieval_id": "pi-query"}
        if endpoint == "/retrieval/pi-query/":
            return {"status": "completed", "retrieved_nodes": [{
                "node_id": "n1", "title": "Động năng", "relevant_contents": [
                    {"page_index": 88, "relevant_content": "Động năng là năng lượng do chuyển động."},
                ],
            }]}
        raise AssertionError(endpoint)

    monkeypatch.setattr(pageindex, "_request", fake_request)
    results = pageindex.pageindex_search("động năng", top_k=2)
    validate_search_results(results, top_k=2, expected_method="pageindex")
    assert results[0]["metadata"]["pdf_page"] == 88
    assert results[0]["id"] == "pageindex:pi-doc:n1:88:0"


def test_pageindex_content_parts_accepts_nested_groups():
    node = {"relevant_contents": [[
        {"page_index": 3, "relevant_content": "Một đoạn."},
    ]]}
    assert pageindex._content_parts(node) == [("Một đoạn.", 3)]


def test_upload_source_map_covers_books_and_articles_without_network(monkeypatch, tmp_path):
    created = []
    monkeypatch.setattr(pageindex, "PDF_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        pageindex, "_render_article_pdf", lambda markdown, pdf: created.append((markdown, pdf))
    )
    sources = pageindex._sources()
    assert len(sources) == 8
    assert len(created) == 5
    assert sources["legal/10.md"].name == "10.pdf"
    assert sources["news/article_01.md"].name == "article_01.pdf"
