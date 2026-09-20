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

from __future__ import annotations

import os
import time

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-3.6-flash",
    "anthropic": "claude-haiku-4-5-20251001",
}

SAFE_REFUSAL = (
    "Tôi không thể xác minh thông tin này từ nguồn hiện có. "
    "Bộ tài liệu của nhóm chưa có đủ dữ liệu để trả lời câu hỏi này."
)

SYSTEM_PROMPT = """Trả lời chỉ từ context được cung cấp.
Mỗi khẳng định phải có citation dạng [Document N] khớp với nhãn trong context.
Nếu thiếu evidence, hãy từ chối xác minh thay vì suy đoán."""

_RETRYABLE_MARKERS = ("429", "500", "503", "rate limit", "overloaded", "unavailable")


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context."""
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


def _model_name() -> str:
    return LLM_MODEL or DEFAULT_MODELS.get(LLM_PROVIDER, "")


def _is_retryable(error: Exception) -> bool:
    message = str(error).lower()
    return any(marker in message for marker in _RETRYABLE_MARKERS)


def _call_openai(system_prompt: str, user_message: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=_model_name(),
        temperature=TEMPERATURE,
        top_p=TOP_P,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def _call_gemini(system_prompt: str, user_message: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=_model_name(),
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=TEMPERATURE,
            top_p=TOP_P,
        ),
    )
    return (response.text or "").strip()


def _call_anthropic(system_prompt: str, user_message: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=_model_name(),
        max_tokens=1024,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    ).strip()


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình, có retry cho lỗi tạm thời."""
    providers = {
        "openai": _call_openai,
        "gemini": _call_gemini,
        "anthropic": _call_anthropic,
    }
    provider = providers.get(LLM_PROVIDER)
    if provider is None:
        raise ValueError(
            "LLM_PROVIDER không hợp lệ. Dùng openai, gemini hoặc anthropic."
        )
    if not _model_name():
        raise ValueError("Thiếu LLM_MODEL cho provider đã chọn.")

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            return provider(system_prompt, user_message)
        except Exception as error:
            last_error = error
            if attempt == MAX_RETRIES - 1 or not _is_retryable(error):
                break
            # 429/500/503 là lỗi tạm thời của provider: backoff rồi thử lại.
            time.sleep(RETRY_BACKOFF * (attempt + 1))
    raise RuntimeError(f"Provider {LLM_PROVIDER} lỗi: {last_error}") from last_error


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    if not isinstance(query, str) or not query.strip():
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    # Reorder chỉ đổi thứ tự trong context; sources vẫn giữ nguyên ID và thứ hạng.
    context = format_context(reorder_for_llm(chunks))
    user_message = f"Context:\n{context}\n\nQuestion: {query.strip()}"
    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:
        print(f"Generation lỗi ({error}), trả safe refusal.")
        return {"answer": SAFE_REFUSAL, "sources": chunks, "retrieval_source": "hybrid"}
    if not answer.strip():
        return {"answer": SAFE_REFUSAL, "sources": chunks, "retrieval_source": "hybrid"}

    # Contract chỉ cho phép hybrid/pageindex/none; nhánh dense-only (A/B) map về hybrid.
    method = chunks[0]["retrieval_method"]
    retrieval_source = "pageindex" if method == "pageindex" else "hybrid"
    return {"answer": answer, "sources": chunks, "retrieval_source": retrieval_source}


if __name__ == "__main__":
    output = generate_with_citation("Vịnh Hạ Long được UNESCO công nhận năm nào?")
    print(output["answer"])
    print("---")
    for source in output["sources"]:
        print(source["id"], round(source["score"], 5), source["metadata"]["title"])
