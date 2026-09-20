from copy import deepcopy
import json

from src.contracts import validate_search_results
from src import task7_reranking as fusion
from src import task8_pageindex_vectorless as pageindex


def test_fusion_is_non_mutating_and_pageindex_parses_results(tmp_path, monkeypatch):
    dense = [{"id": "a", "score": 0.9}, {"id": "b", "score": 0.8}]
    bm25 = [{"id": "b", "score": 8.0}]
    original = deepcopy([dense, bm25])
    assert fusion.rerank_rrf([dense, bm25], 2)[0]["id"] == "b"
    assert [dense, bm25] == original

    cache = tmp_path / "pageindex_doc_ids.json"
    cache.write_text(
        json.dumps({"policy.pdf": {"doc_id": "doc-1", "sha256": "abc"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(pageindex, "CACHE_FILE", cache)
    monkeypatch.setattr(
        pageindex,
        "_retrieve_document",
        lambda _doc_id, _query: [
            {
                "title": "Policy",
                "relevant_contents": [[
                    {
                        "physical_index": "<physical_index_2>",
                        "relevant_content": "Grounded policy text",
                    }
                ]],
            }
        ],
    )
    results = pageindex.pageindex_search("policy", 1)
    validate_search_results(results, top_k=1, expected_method="pageindex")
    assert results[0]["metadata"]["chunk_index"] == 2
