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

SYSTEM_PROMPT = """Trả lời chỉ từ context được cung cấp.
Mỗi khẳng định phải có citation. Nếu thiếu evidence, hãy từ chối xác minh."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context."""
    # TODO: Implement document reordering.
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    # TODO: Format chunks để LLM tạo citation kiểm chứng được.
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        parts.append(
            f"[Document {index} | Title: {metadata['title']} | "
            f"Source: {metadata['source']}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


_GENAI_CLIENT = None
_OPENAI_CLIENT = None
_ANTHROPIC_CLIENT = None


def get_genai_client():
    global _GENAI_CLIENT
    if _GENAI_CLIENT is None:
        from google import genai
        _GENAI_CLIENT = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    return _GENAI_CLIENT


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    # TODO: Dispatch theo LLM_PROVIDER.
    provider = LLM_PROVIDER.lower()
    if provider == "openai":
        global _OPENAI_CLIENT
        if _OPENAI_CLIENT is None:
            from openai import OpenAI
            _OPENAI_CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        client = _OPENAI_CLIENT
        model = LLM_MODEL or "gpt-4o-mini"
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.choices[0].message.content or ""
    elif provider == "gemini":
        client = get_genai_client()
        model = LLM_MODEL or "gemini-3.5-flash-lite"
        response = client.models.generate_content(
            model=model,
            contents=user_message,
            config={"system_instruction": system_prompt, "temperature": TEMPERATURE},
        )
        return response.text or ""
    elif provider == "anthropic":
        global _ANTHROPIC_CLIENT
        if _ANTHROPIC_CLIENT is None:
            import anthropic
            _ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        client = _ANTHROPIC_CLIENT
        model = LLM_MODEL or "claude-3-5-sonnet-latest"
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
        )
        return response.content[0].text
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def stream_llm(system_prompt: str, user_message: str):
    """Generator streaming tokens từ LLM provider."""
    provider = LLM_PROVIDER.lower()
    if provider == "gemini":
        client = get_genai_client()
        model = LLM_MODEL or "gemini-3.5-flash-lite"
        response = client.models.generate_content_stream(
            model=model,
            contents=user_message,
            config={"system_instruction": system_prompt, "temperature": TEMPERATURE},
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
    elif provider == "openai":
        global _OPENAI_CLIENT
        if _OPENAI_CLIENT is None:
            from openai import OpenAI
            _OPENAI_CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        client = _OPENAI_CLIENT
        model = LLM_MODEL or "gpt-4o-mini"
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
    else:
        yield call_llm(system_prompt, user_message)


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    # TODO: Implement end-to-end generation.
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
            "retrieval_source": "none",
        }
    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"
    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": chunks,
            "retrieval_source": chunks[0]["retrieval_method"],
        }
    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": chunks[0]["retrieval_method"],
    }


def generate_stream(query: str, top_k: int = TOP_K):
    """Retrieve chunks và stream answer, trả về generator cùng sources metadata."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        def empty_gen():
            yield "Tôi không thể xác minh thông tin này từ nguồn hiện có."
        return empty_gen(), [], "none"

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"
    method = chunks[0]["retrieval_method"]

    def token_generator():
        try:
            for token in stream_llm(SYSTEM_PROMPT, user_message):
                yield token
        except Exception:
            yield "Tôi không thể xác minh thông tin này từ nguồn hiện có."

    return token_generator(), chunks, method


if __name__ == "__main__":
    print(generate_with_citation("test query"))
