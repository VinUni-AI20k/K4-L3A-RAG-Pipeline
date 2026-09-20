"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
"""

import os

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "")

SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

SYSTEM_PROMPT = """Trả lời chỉ từ context được cung cấp.
Mỗi khẳng định phải có citation dạng [Document N] tương ứng với số thứ tự
trong context. Nếu thiếu evidence, hãy từ chối xác minh thay vì bịa thông tin."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context (giảm lost-in-the-middle)."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        parts.append(
            f"[Document {index} | Title: {metadata['title']} | "
            f"Source: {metadata['source']}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    if LLM_PROVIDER == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model=LLM_MODEL or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.choices[0].message.content

    if LLM_PROVIDER == "anthropic":
        from anthropic import Anthropic

        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model=LLM_MODEL or "claude-haiku-4-5-20251001",
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=1024,
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.content[0].text

    if LLM_PROVIDER == "gemini":
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = client.models.generate_content(
            model=LLM_MODEL or "gemini-2.0-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=TEMPERATURE,
                top_p=TOP_P,
            ),
        )
        return response.text

    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")


def generate_with_mode(query: str, top_k: int = TOP_K, use_reranking: bool = True) -> dict:
    """Như generate_with_citation, nhưng cho chọn retrieval mode (dùng để so sánh
    dense-only vs hybrid+RRF trong UI/evaluation). generate_with_citation() gọi hàm
    này với use_reranking=True để giữ nguyên contract signature công khai."""
    chunks = retrieve(query, top_k=top_k, use_reranking=use_reranking)
    if not chunks:
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:
        print(f"LLM call failed: {error}")
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    if not answer or not answer.strip():
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": chunks[0]["retrieval_method"],
    }


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:
        print(f"LLM call failed: {error}")
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    if not answer or not answer.strip():
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": chunks[0]["retrieval_method"],
    }


QUERY_REWRITE_PROMPT = """Dựa vào lịch sử hội thoại, viết lại câu hỏi cuối cùng của
người dùng thành một câu hỏi độc lập, đầy đủ ngữ cảnh, hiểu được mà không cần xem
lịch sử. Chỉ trả về câu hỏi đã viết lại, không giải thích thêm."""


def rewrite_standalone_query(query: str, history: list[dict]) -> str:
    """Viết lại câu hỏi follow-up thành câu hỏi độc lập dựa trên lịch sử hội thoại
    (bonus: conversation memory). Không có lịch sử thì trả nguyên câu hỏi gốc."""
    if not history:
        return query
    turns = "\n".join(f"{h['role']}: {h['content']}" for h in history[-6:])
    user_message = f"Lịch sử hội thoại:\n{turns}\n\nCâu hỏi mới: {query}"
    try:
        rewritten = call_llm(QUERY_REWRITE_PROMPT, user_message)
        return rewritten.strip() or query
    except Exception as error:
        print(f"Query rewrite failed: {error}")
        return query


def generate_with_history(
    query: str,
    history: list[dict] | None = None,
    top_k: int = TOP_K,
    use_reranking: bool = True,
) -> dict:
    """Như generate_with_mode, nhưng dùng lịch sử hội thoại để viết lại câu hỏi
    follow-up thành câu hỏi độc lập trước khi retrieve, và đưa lịch sử gần đây
    vào prompt sinh câu trả lời (bonus: conversation memory)."""
    history = history or []
    standalone_query = rewrite_standalone_query(query, history)

    chunks = retrieve(standalone_query, top_k=top_k, use_reranking=use_reranking)
    if not chunks:
        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
            "standalone_query": standalone_query,
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    history_text = "\n".join(f"{h['role']}: {h['content']}" for h in history[-4:])
    user_message = (
        (f"Lịch sử hội thoại gần đây:\n{history_text}\n\n" if history_text else "")
        + f"Context:\n{context}\n\nQuestion: {query}"
    )

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:
        print(f"LLM call failed: {error}")
        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
            "standalone_query": standalone_query,
        }

    if not answer or not answer.strip():
        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
            "standalone_query": standalone_query,
        }

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": chunks[0]["retrieval_method"],
        "standalone_query": standalone_query,
    }


if __name__ == "__main__":
    print(generate_with_citation("test query"))
