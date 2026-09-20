"""Focused offline checks for semantic search and cited generation."""

import pytest

from src.contracts import validate_generation_result, validate_search_results


def _chunk(item_id: str, score: float = 0.8, method: str = "hybrid") -> dict:
    return {
        "id": item_id,
        "content": "Học phí được thu theo học kỳ.",
        "score": score,
        "metadata": {
            "source": "tuition.md",
            "title": "Quy định học phí",
            "doc_type": "legal",
            "url": None,
            "chunk_index": int(item_id[-1]),
        },
        "retrieval_method": method,
    }


def test_semantic_search_sorts_deduplicates_and_converts_cosine_distance(monkeypatch):
    import src.task5_semantic_search as semantic

    class Collection:
        def query(self, **kwargs):
            assert kwargs["query_embeddings"] == [[0.1, 0.2]]
            assert kwargs["n_results"] == 3
            return {
                "ids": [["chunk-1", "chunk-0", "chunk-1"]],
                "documents": [["second", "first", "duplicate"]],
                "metadatas": [[_chunk("chunk-1")["metadata"], _chunk("chunk-0")["metadata"], _chunk("chunk-1")["metadata"]]],
                "distances": [[0.4, 0.1, 0.3]],
            }

    monkeypatch.setattr(semantic, "embed_texts", lambda texts: [[0.1, 0.2]])
    monkeypatch.setattr(semantic, "get_collection", Collection)
    results = semantic.semantic_search("học phí", top_k=3)
    validate_search_results(results, top_k=3, expected_method="dense")
    assert [item["id"] for item in results] == ["chunk-0", "chunk-1"]
    assert [item["score"] for item in results] == pytest.approx([0.9, 0.6])


def test_generate_with_citation_keeps_source_ids_and_order(monkeypatch):
    import src.task10_generation as generation

    chunks = [_chunk("chunk-0", 0.9), _chunk("chunk-1", 0.8), _chunk("chunk-2", 0.7)]
    monkeypatch.setattr(generation, "retrieve", lambda query, top_k: chunks)

    def answer(system_prompt, user_message):
        assert "ID: chunk-0" in user_message
        assert "Title: Quy định học phí" in user_message
        assert "Source: tuition.md" in user_message
        return "Học phí được thu theo học kỳ [chunk-0]."

    monkeypatch.setattr(generation, "call_llm", answer)
    output = generation.generate_with_citation("Khi nào thu học phí?")
    validate_generation_result(output)
    assert output["answer"].endswith("[chunk-0].")
    assert output["sources"] == chunks
    assert output["retrieval_source"] == "hybrid"


@pytest.mark.parametrize("answer", ["Không rõ.", "Có quy định [unknown].", ""])
def test_generation_refuses_uncited_or_unknown_sources(monkeypatch, answer):
    import src.task10_generation as generation

    monkeypatch.setattr(generation, "retrieve", lambda query, top_k: [_chunk("chunk-0")])
    monkeypatch.setattr(generation, "call_llm", lambda system, user: answer)
    output = generation.generate_with_citation("Hỏi")
    validate_generation_result(output)
    assert output == generation._refusal()


def test_generation_refuses_provider_error_and_no_evidence(monkeypatch):
    import src.task10_generation as generation

    monkeypatch.setattr(generation, "retrieve", lambda query, top_k: [])
    assert generation.generate_with_citation("Hỏi") == generation._refusal()
    monkeypatch.setattr(generation, "retrieve", lambda query, top_k: [_chunk("chunk-0")])

    def unavailable(system, user):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(generation, "call_llm", unavailable)
    assert generation.generate_with_citation("Hỏi") == generation._refusal()


def test_generation_marks_pageindex_source(monkeypatch):
    import src.task10_generation as generation

    monkeypatch.setattr(generation, "retrieve", lambda query, top_k: [_chunk("chunk-0", method="pageindex")])
    monkeypatch.setattr(generation, "call_llm", lambda system, user: "Thông tin [chunk-0].")
    assert generation.generate_with_citation("Hỏi")["retrieval_source"] == "pageindex"


def test_openai_dispatch_returns_plain_text_without_network(monkeypatch):
    import openai
    import src.task10_generation as generation

    class Client:
        def __init__(self):
            self.chat = type("Chat", (), {
                "completions": type("Completions", (), {
                    "create": lambda self, **kwargs: type("Response", (), {
                        "choices": [type("Choice", (), {
                            "message": type("Message", (), {"content": "OpenAI answer"})()
                        })()]
                    })()
                })()
            })()

    monkeypatch.setattr(generation, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(generation, "LLM_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(openai, "OpenAI", Client)
    assert generation.call_llm("system", "user") == "OpenAI answer"


def test_gemini_dispatch_returns_plain_text_without_network(monkeypatch):
    from google import genai
    import src.task10_generation as generation

    class Client:
        def __init__(self, **kwargs):
            self.models = type("Models", (), {
                "generate_content": lambda self, **kwargs: type(
                    "Response", (), {"text": "Gemini answer"}
                )()
            })()

    monkeypatch.setattr(generation, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(generation, "LLM_MODEL", "test-model")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(genai, "Client", Client)
    assert generation.call_llm("system", "user") == "Gemini answer"


def test_anthropic_dispatch_returns_plain_text_without_network(monkeypatch):
    import anthropic
    import src.task10_generation as generation

    class Client:
        def __init__(self):
            self.messages = type("Messages", (), {
                "create": lambda self, **kwargs: type("Response", (), {
                    "content": [type("Block", (), {"type": "text", "text": "Anthropic answer"})()]
                })()
            })()

    monkeypatch.setattr(generation, "LLM_PROVIDER", "anthropic")
    monkeypatch.setattr(generation, "LLM_MODEL", "test-model")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(anthropic, "Anthropic", Client)
    assert generation.call_llm("system", "user") == "Anthropic answer"
