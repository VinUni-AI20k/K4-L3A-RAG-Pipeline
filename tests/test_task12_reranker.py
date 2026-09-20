"""Offline tests cho cross-encoder reranker (Task 12) và cách Task 9 dùng nó."""

import pytest

from src.contracts import validate_search_results
from tests.test_contracts import result


@pytest.fixture
def fused():
    return [
        result("chunk-0", 0.0325, "hybrid", "Band 1 boilerplate: responses of 20 words or fewer."),
        result("chunk-1", 0.0164, "hybrid", "Band 7 Lexical Resource: sufficient range of vocabulary."),
        result("chunk-2", 0.0161, "hybrid", "Written by David S. Wills."),
    ]


def test_cross_encoder_reorders_by_score_and_keeps_contract(monkeypatch, fused):
    import src.task12_cross_encoder_rerank as reranker

    monkeypatch.setattr(reranker, "score_pairs", lambda query, passages: [0.01, 0.97, 0.20])
    original = [dict(item) for item in fused]

    output = reranker.rerank_cross_encoder("band 7 lexical resource", fused, top_k=2)

    assert [item["id"] for item in output] == ["chunk-1", "chunk-2"]
    assert [item["score"] for item in output] == [0.97, 0.20]
    assert fused == original, "input không được bị sửa"
    validate_search_results(output, top_k=2, expected_method="hybrid")


def test_cross_encoder_ties_keep_rrf_order(monkeypatch, fused):
    import src.task12_cross_encoder_rerank as reranker

    monkeypatch.setattr(reranker, "score_pairs", lambda query, passages: [0.5, 0.5, 0.5])
    output = reranker.rerank_cross_encoder("q", fused, top_k=3)
    assert [item["id"] for item in output] == ["chunk-0", "chunk-1", "chunk-2"]


def test_cross_encoder_handles_empty_input(monkeypatch):
    import src.task12_cross_encoder_rerank as reranker

    called = {"n": 0}

    def fail(query, passages):
        called["n"] += 1
        raise AssertionError("không được gọi model khi input rỗng")

    monkeypatch.setattr(reranker, "score_pairs", fail)
    assert reranker.rerank_cross_encoder("q", [], top_k=5) == []
    assert reranker.rerank_cross_encoder("", [result("chunk-0", 1.0)], top_k=5) == []
    assert reranker.rerank_cross_encoder("q", [result("chunk-0", 1.0)], top_k=0) == []
    assert called["n"] == 0


def test_pipeline_reranks_after_single_rrf(monkeypatch, fused):
    import src.task9_retrieval_pipeline as pipeline

    dense = [result("chunk-0", 0.9, "dense")]
    sparse = [result("chunk-1", 4.0, "bm25")]
    calls = {"rrf": 0, "ce": 0}

    def fake_rrf(lists, top_k):
        calls["rrf"] += 1
        assert lists == [dense, sparse]
        assert top_k == 4, "RRF phải lấy dư ứng viên (2×top_k) cho cross-encoder"
        return fused

    def fake_ce(query, results, top_k):
        calls["ce"] += 1
        assert results == fused
        return [dict(fused[1], score=0.97), dict(fused[2], score=0.2)][:top_k]

    monkeypatch.setattr(pipeline, "semantic_search", lambda query, top_k: dense)
    monkeypatch.setattr(pipeline, "lexical_search", lambda query, top_k: sparse)
    monkeypatch.setattr(pipeline, "rerank_rrf", fake_rrf)
    monkeypatch.setattr(pipeline, "rerank_cross_encoder", fake_ce)
    monkeypatch.setattr(pipeline, "pageindex_search", lambda query, top_k: [])

    detail = pipeline.retrieve_detailed("q", top_k=2, score_threshold=0.5, use_cross_encoder=True)

    assert calls == {"rrf": 1, "ce": 1}
    assert detail["reranked"] is True
    assert detail["reranker_error"] is None
    assert detail["fallback_tried"] is False
    assert [item["id"] for item in detail["results"]] == ["chunk-1", "chunk-2"]
    validate_search_results(detail["results"], top_k=2, expected_method="hybrid")


def test_pipeline_falls_back_to_rrf_when_reranker_fails(monkeypatch, fused):
    import src.task9_retrieval_pipeline as pipeline

    dense = [result("chunk-0", 0.9, "dense")]

    def broken(query, results, top_k):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(pipeline, "semantic_search", lambda query, top_k: dense)
    monkeypatch.setattr(pipeline, "lexical_search", lambda query, top_k: [])
    monkeypatch.setattr(pipeline, "rerank_rrf", lambda lists, top_k: fused)
    monkeypatch.setattr(pipeline, "rerank_cross_encoder", broken)
    monkeypatch.setattr(pipeline, "pageindex_search", lambda query, top_k: [])

    detail = pipeline.retrieve_detailed("q", top_k=2, score_threshold=0.5, use_cross_encoder=True)

    assert detail["reranked"] is False
    assert "model unavailable" in detail["reranker_error"]
    assert detail["results"] == fused[:2]


def test_pipeline_skips_cross_encoder_without_rrf(monkeypatch):
    import src.task9_retrieval_pipeline as pipeline

    dense = [result("chunk-0", 0.9, "dense"), result("chunk-1", 0.8, "dense")]

    def must_not_run(*args, **kwargs):
        raise AssertionError("cross-encoder không được chạy khi use_reranking=False")

    monkeypatch.setattr(pipeline, "semantic_search", lambda query, top_k: dense)
    monkeypatch.setattr(pipeline, "lexical_search", lambda query, top_k: [])
    monkeypatch.setattr(pipeline, "rerank_rrf", must_not_run)
    monkeypatch.setattr(pipeline, "rerank_cross_encoder", must_not_run)
    monkeypatch.setattr(pipeline, "pageindex_search", lambda query, top_k: [])

    detail = pipeline.retrieve_detailed(
        "q", top_k=1, score_threshold=0.5, use_reranking=False, use_cross_encoder=True
    )
    assert detail["reranked"] is False
    assert detail["results"] == dense[:1]
