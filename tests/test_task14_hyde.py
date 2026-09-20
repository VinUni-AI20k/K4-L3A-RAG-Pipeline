"""Offline tests cho HyDE (Task 14) và cách Task 9 gộp 3 danh sách."""

from tests.test_contracts import result


def test_generate_hypothetical_trims_and_survives_llm_error(monkeypatch):
    import src.task10_generation as generation
    import src.task14_hyde as hyde

    monkeypatch.setattr(generation, "call_llm", lambda system, user: "  Band 7   requires\n a sufficient range. " + "x" * 2000)
    text = hyde.generate_hypothetical("Band 7 lexical?")
    assert text.startswith("Band 7 requires a sufficient range.")
    assert len(text) == hyde.MAX_HYPOTHETICAL_CHARS

    def broken(system, user):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(generation, "call_llm", broken)
    assert hyde.generate_hypothetical("q") == ""
    assert hyde.expand_query("q") == "q", "lỗi LLM thì dùng query gốc"


def test_pipeline_fuses_three_lists_once_with_hyde(monkeypatch):
    import src.task9_retrieval_pipeline as pipeline

    dense_raw = [result("chunk-0", 0.9, "dense")]
    dense_hyde = [result("chunk-1", 0.8, "dense")]
    sparse_hyde = [result("chunk-2", 3.0, "bm25")]
    fused = [result("chunk-1", 0.03, "hybrid"), result("chunk-0", 0.02, "hybrid")]
    seen = {"dense": [], "sparse": [], "rrf": 0}

    def fake_dense(query, top_k):
        seen["dense"].append(query)
        return dense_raw if query == "q" else dense_hyde

    def fake_sparse(query, top_k):
        seen["sparse"].append(query)
        return sparse_hyde

    def fake_rrf(lists, top_k):
        seen["rrf"] += 1
        assert lists == [dense_raw, dense_hyde, sparse_hyde]
        return fused

    monkeypatch.setattr(pipeline, "semantic_search", fake_dense)
    monkeypatch.setattr(pipeline, "lexical_search", fake_sparse)
    monkeypatch.setattr(pipeline, "rerank_rrf", fake_rrf)
    monkeypatch.setattr(pipeline, "expand_query", lambda query: "q\nhypothetical passage")
    monkeypatch.setattr(pipeline, "pageindex_search", lambda query, top_k: [])

    detail = pipeline.retrieve_detailed("q", top_k=2, score_threshold=0.5, use_cross_encoder=False, use_hyde=True)

    assert seen["rrf"] == 1
    assert seen["dense"] == ["q", "q\nhypothetical passage"]
    assert seen["sparse"] == ["q\nhypothetical passage"]
    assert detail["hyde_query"] == "q\nhypothetical passage"
    assert detail["best_dense_score"] == 0.9, "fallback vẫn dựa trên dense của query gốc"
    assert detail["results"] == fused


def test_pipeline_uses_two_lists_when_hyde_returns_nothing(monkeypatch):
    import src.task9_retrieval_pipeline as pipeline

    dense = [result("chunk-0", 0.9, "dense")]
    sparse = [result("chunk-1", 3.0, "bm25")]
    fused = [result("chunk-0", 0.03, "hybrid")]

    monkeypatch.setattr(pipeline, "semantic_search", lambda query, top_k: dense)
    monkeypatch.setattr(pipeline, "lexical_search", lambda query, top_k: sparse)
    monkeypatch.setattr(pipeline, "rerank_rrf", lambda lists, top_k: (lists == [dense, sparse]) and fused)
    monkeypatch.setattr(pipeline, "expand_query", lambda query: query)   # LLM lỗi → query gốc
    monkeypatch.setattr(pipeline, "pageindex_search", lambda query, top_k: [])

    detail = pipeline.retrieve_detailed("q", top_k=1, score_threshold=0.5, use_cross_encoder=False, use_hyde=True)
    assert detail["hyde_query"] is None
    assert detail["results"] == fused


def test_pipeline_ignores_hyde_without_rrf(monkeypatch):
    import src.task9_retrieval_pipeline as pipeline

    dense = [result("chunk-0", 0.9, "dense")]

    def must_not_run(*args, **kwargs):
        raise AssertionError("HyDE không được chạy khi use_reranking=False")

    monkeypatch.setattr(pipeline, "semantic_search", lambda query, top_k: dense)
    monkeypatch.setattr(pipeline, "lexical_search", lambda query, top_k: [])
    monkeypatch.setattr(pipeline, "expand_query", must_not_run)
    monkeypatch.setattr(pipeline, "pageindex_search", lambda query, top_k: [])

    detail = pipeline.retrieve_detailed("q", top_k=1, score_threshold=0.5, use_reranking=False, use_hyde=True)
    assert detail["hyde_query"] is None and detail["results"] == dense
