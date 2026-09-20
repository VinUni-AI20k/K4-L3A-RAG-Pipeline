from src.contracts import validate_generation_result
from src import task10_generation as generation


def test_fpt_provider_dispatch(monkeypatch):
    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            assert kwargs["model"] == "DeepSeek-V4-Flash"
            assert [message["role"] for message in kwargs["messages"]] == ["system", "user"]
            message = type("Message", (), {"content": "Answer [S1]."})()
            choice = type("Choice", (), {"message": message})()
            return type("Response", (), {"choices": [choice]})()

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["api_key"] == "test-key"
            assert kwargs["base_url"] == "https://mkp-api.fptcloud.com"
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

    monkeypatch.setenv("FPT_API_KEY", "test-key")
    monkeypatch.setattr(generation, "LLM_PROVIDER", "fpt")
    monkeypatch.setattr(generation, "LLM_MODEL", "DeepSeek-V4-Flash")
    monkeypatch.setattr("openai.OpenAI", FakeClient)

    assert generation.call_llm("system", "user") == "Answer [S1]."

def test_generation_maps_citations_and_refuses_invalid_output(monkeypatch):
    chunks = [
        {
            "id": "chunk-0",
            "content": "Registration starts on Monday.",
            "score": 0.03,
            "metadata": {
                "source": "notice.md",
                "title": "Registration notice",
                "doc_type": "news",
                "url": "https://example.test/notice",
                "chunk_index": 0,
            },
            "retrieval_method": "hybrid",
        }
    ]
    monkeypatch.setattr(generation, "retrieve", lambda _query, top_k: chunks)
    monkeypatch.setattr(
        generation,
        "call_llm",
        lambda _system, _message: "Registration starts on Monday [S1].",
    )
    result = generation.generate_with_citation("When?", 1)
    validate_generation_result(result)
    assert result["sources"] == chunks
    assert result["retrieval_source"] == "hybrid"

    monkeypatch.setattr(
        generation,
        "call_llm",
        lambda _system, _message: "Unsupported answer [S2].",
    )
    refused = generation.generate_with_citation("When?", 1)
    validate_generation_result(refused)
    assert refused["sources"] == []
    assert refused["retrieval_source"] == "none"

def test_generation_keeps_ranked_sources_while_reordering_context(monkeypatch):
    chunks = [
        {
            "id": f"chunk-{index}",
            "content": f"Evidence {index}.",
            "score": 1 - index / 10,
            "metadata": {
                "source": "notice.md",
                "title": "Registration notice",
                "doc_type": "news",
                "url": None,
                "chunk_index": index,
            },
            "retrieval_method": "hybrid",
        }
        for index in range(5)
    ]
    prompts = []
    monkeypatch.setattr(generation, "retrieve", lambda _query, top_k: chunks)
    monkeypatch.setattr(
        generation,
        "call_llm",
        lambda _system, message: prompts.append(message) or "Evidence [S2].",
    )

    result = generation.generate_with_citation("When?", 5)

    validate_generation_result(result)
    assert [source["id"] for source in result["sources"]] == [
        f"chunk-{index}" for index in range(5)
    ]
    assert "[S2]\nTitle: Registration notice" in prompts[0]
    assert prompts[0].index("[S2]") > prompts[0].index("[S5]")
