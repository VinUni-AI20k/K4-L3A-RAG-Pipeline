"""Offline tests cho conversation memory (Task 13)."""

from src.contracts import validate_generation_result
from tests.test_task5_task10 import _chunk


def test_trim_history_drops_refusals_and_keeps_recent(monkeypatch):
    import src.task13_conversation_memory as memory

    history = [{"role": "user", "content": f"q{i}"} for i in range(10)]
    history.insert(3, {"role": "assistant", "content": memory.SAFE_REFUSAL})
    history.insert(5, {"role": "system", "content": "ignored"})
    kept = memory.trim_history(history)
    assert len(kept) == memory.MAX_HISTORY_TURNS
    assert all(turn["content"] != memory.SAFE_REFUSAL for turn in kept)
    assert all(turn["role"] in {"user", "assistant"} for turn in kept)
    assert kept[-1]["content"] == "q9"


def test_condense_skips_llm_without_history(monkeypatch):
    import src.task13_conversation_memory as memory

    def must_not_call(system, user):
        raise AssertionError("không được gọi LLM khi không có lịch sử")

    monkeypatch.setattr(memory, "call_llm", must_not_call)
    assert memory.condense_query("How many words for Task 2?", []) == "How many words for Task 2?"


def test_condense_rewrites_follow_up_and_strips_old_citations(monkeypatch):
    import src.task13_conversation_memory as memory

    seen = {}

    def fake_llm(system, user):
        seen["user"] = user
        return '  "How many words must I write for IELTS Writing Task 1?"  '

    monkeypatch.setattr(memory, "call_llm", fake_llm)
    history = [
        {"role": "user", "content": "How many words for Task 2?"},
        {"role": "assistant", "content": "At least 250 words [legal/x.md::chunk-1]."},
    ]
    standalone = memory.condense_query("And for Task 1?", history)
    assert standalone == "How many words must I write for IELTS Writing Task 1?"
    assert "Latest question: And for Task 1?" in seen["user"]
    assert "At least 250 words ." in seen["user"]
    assert "chunk-1" not in seen["user"], "citation cũ phải bị bỏ khỏi lịch sử"


def test_condense_falls_back_to_original_on_llm_error(monkeypatch):
    import src.task13_conversation_memory as memory

    def broken(system, user):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(memory, "call_llm", broken)
    history = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]
    assert memory.condense_query("And Task 1?", history) == "And Task 1?"


def test_answer_with_memory_retrieves_on_standalone_and_passes_history(monkeypatch):
    import src.task10_generation as generation
    import src.task13_conversation_memory as memory

    chunks = [_chunk("chunk-0", 0.9)]
    calls = {}

    monkeypatch.setattr(memory, "condense_query", lambda query, history: "standalone Task 1 words")

    def fake_retrieve(query, top_k):
        calls["retrieve_query"] = query
        return chunks

    def fake_llm(system, user):
        calls["user"] = user
        return "Ít nhất 150 từ [chunk-0]."

    monkeypatch.setattr(memory, "retrieve", fake_retrieve)
    monkeypatch.setattr(generation, "call_llm", fake_llm)

    history = [
        {"role": "user", "content": "Task 2 bao nhiêu từ?"},
        {"role": "assistant", "content": "Ít nhất 250 từ [legal/x.md::chunk-3]."},
    ]
    result = memory.answer_with_memory("Còn Task 1?", history, top_k=3)

    assert calls["retrieve_query"] == "standalone Task 1 words"
    assert "Conversation so far" in calls["user"]
    assert "Ít nhất 250 từ" in calls["user"] and "chunk-3" not in calls["user"]
    assert calls["user"].rstrip().endswith("Question: Còn Task 1?"), "câu hỏi gốc giữ nguyên trong prompt"
    assert result["standalone_query"] == "standalone Task 1 words"
    assert result["answer"] == "Ít nhất 150 từ [chunk-0]."
    validate_generation_result({k: v for k, v in result.items() if k != "standalone_query"})


def test_generate_from_chunks_without_history_is_unchanged(monkeypatch):
    import src.task10_generation as generation

    seen = {}

    def fake_llm(system, user):
        seen["user"] = user
        return "OK [chunk-0]."

    monkeypatch.setattr(generation, "call_llm", fake_llm)
    generation.generate_from_chunks("Hỏi", [_chunk("chunk-0")])
    assert "Conversation so far" not in seen["user"]
