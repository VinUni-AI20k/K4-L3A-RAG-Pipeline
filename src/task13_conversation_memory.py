"""
Task 13 (bonus) — Conversation memory cho câu hỏi nối tiếp.

Câu hỏi nối tiếp như "Còn Task 1 thì sao?" hay "Band 8 thì khác gì?" không tự
đứng được: embedding và BM25 chỉ thấy "Task 1", không biết đang nói về số từ
tối thiểu. Hai bước:

    1. condense_query(): nếu có lịch sử, nhờ LLM viết lại câu hỏi thành câu
       độc lập, giữ nguyên ngôn ngữ của người dùng. Câu này dùng cho retrieval.
       Không có lịch sử thì trả nguyên văn, không tốn lời gọi LLM.
    2. generate_from_chunks(..., history=...): các lượt gần nhất được đưa vào
       prompt (đã bỏ citation cũ) để LLM hiểu ngữ cảnh; citation vẫn phải map
       về Context hiện tại, safe refusal không đổi.

Chỉ giữ MAX_HISTORY_TURNS lượt gần nhất để prompt không phình; lượt refusal
được bỏ vì không mang thông tin.

Chạy demo 3 lượt (ghi transcript vào group_project/evaluation/results/):
    python -m src.task13_conversation_memory
"""

import re
import sys
from datetime import datetime
from pathlib import Path

from .task9_retrieval_pipeline import retrieve
from .task10_generation import SAFE_REFUSAL, call_llm, format_history, generate_from_chunks


MAX_HISTORY_TURNS = 6   # 3 cặp hỏi–đáp
TOP_K = 5

CONDENSE_PROMPT = """Rewrite the user's latest question as a single self-contained question that can be used
to search documents without reading the conversation.
Rules:
- Resolve references such as "it", "that", "the other one", "which one", "and for X?" using the conversation.
- Write the rewritten question in the SAME language as the latest question (English stays English, Vietnamese stays Vietnamese).
- Do not answer the question, do not add facts, do not explain.
- If the latest question is already self-contained, return it unchanged.
Output only the rewritten question."""

DEMO_TURNS = [
    "How many words must I write for IELTS Writing Task 2?",
    "And for Task 1?",
    "Which one carries more weight in the final score?",
]


def trim_history(history: list[dict] | None) -> list[dict]:
    """Giữ các lượt user/assistant gần nhất, bỏ lượt refusal."""
    if not history:
        return []
    kept = [
        {"role": turn["role"], "content": str(turn.get("content", ""))}
        for turn in history
        if turn.get("role") in {"user", "assistant"}
        and str(turn.get("content", "")).strip()
        and turn.get("content") != SAFE_REFUSAL
    ]
    return kept[-MAX_HISTORY_TURNS:]


def condense_query(query: str, history: list[dict]) -> str:
    """Viết lại câu hỏi nối tiếp thành câu độc lập; lỗi LLM thì dùng nguyên văn."""
    if not history:
        return query
    rendered = format_history(history)
    if not rendered:
        return query
    try:
        rewritten = call_llm(
            CONDENSE_PROMPT,
            f"Conversation so far:\n{rendered}\n\nLatest question: {query}",
        )
    except Exception:  # noqa: BLE001 - memory là tiện ích, không được chặn câu trả lời
        return query
    rewritten = re.sub(r"\s+", " ", rewritten).strip().strip('"')
    return rewritten or query


def answer_with_memory(query: str, history: list[dict] | None = None, top_k: int = TOP_K) -> dict:
    """GenerationResult kèm ``standalone_query`` đã dùng để retrieval."""
    if not query.strip() or top_k <= 0:
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none", "standalone_query": query}

    turns = trim_history(history)
    standalone = condense_query(query, turns)
    try:
        chunks = retrieve(standalone, top_k=top_k)
    except Exception:  # noqa: BLE001
        chunks = []
    result = generate_from_chunks(query, chunks[:top_k], history=turns)
    return {**result, "standalone_query": standalone}


def run_demo(turns: list[str], output: Path | None = None) -> str:
    """Chạy hội thoại nhiều lượt và trả transcript Markdown."""
    history: list[dict] = []
    lines = [
        "# Conversation memory demo",
        "",
        f"- Date: {datetime.now().isoformat(timespec='seconds')}",
        f"- Script: `python -m src.task13_conversation_memory`",
        f"- top_k: {TOP_K}, history window: {MAX_HISTORY_TURNS} turns",
        "",
    ]
    for index, query in enumerate(turns, 1):
        result = answer_with_memory(query, history, top_k=TOP_K)
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": result["answer"]})
        cited = ", ".join(f"`{s['id']}`" for s in result["sources"][:3]) or "—"
        lines += [
            f"## Turn {index}",
            "",
            f"- **User:** {query}",
            f"- **Standalone query (retrieval):** {result['standalone_query']}",
            f"- **Retrieval source:** {result['retrieval_source']}; top sources: {cited}",
            f"- **Assistant:** {result['answer']}",
            "",
        ]
        print(f"[{index}] {query}\n    -> {result['standalone_query']}\n    {result['answer'][:160]}\n")
    transcript = "\n".join(lines)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(transcript + "\n", encoding="utf-8")
        print(f"Transcript: {output}")
    return transcript


if __name__ == "__main__":
    turns = sys.argv[1:] or DEMO_TURNS
    out = Path(__file__).resolve().parent.parent / "group_project" / "evaluation" / "results" / "memory_demo.md"
    run_demo(turns, out)
