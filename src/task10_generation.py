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

load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3
MAX_TOKENS = 1_024

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "")

SYSTEM_PROMPT = """Trả lời chỉ từ context được cung cấp.
Mỗi khẳng định phải có citation. Nếu thiếu evidence, hãy từ chối xác minh."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context."""
    # TODO: Implement document reordering.
    #
    # if len(chunks) <= 2:
    #     return list(chunks)
    # front = chunks[::2]
    # back = chunks[1::2]
    # return front + back[::-1]
    # ``chunks`` are already sorted by relevance.  Alternating items places
    # high-ranked evidence at both ends of the prompt, without changing the
    # caller's list or dropping a chunk.
    if len(chunks) <= 2:
        return list(chunks)
    return chunks[::2] + chunks[1::2][::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    # TODO: Format chunks để LLM tạo citation kiểm chứng được.
    #
    # parts = []
    # for index, chunk in enumerate(chunks, 1):
    #     metadata = chunk["metadata"]
    #     parts.append(
    #         f"[Document {index} | Title: {metadata['title']} | "
    #         f"Source: {metadata['source']}]\n{chunk['content']}"
    #     )
    # return "\n\n---\n\n".join(parts)
    parts: list[str] = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        chunk_id = str(chunk.get("id", "unknown"))
        title = str(metadata.get("title", "Unknown title"))
        source = str(metadata.get("source", "Unknown source"))
        content = str(chunk.get("content", "")).strip()
        # The stable chunk ID lets citations map directly back to ``sources``.
        parts.append(
            f"[Document {index} | Citation: {chunk_id} | Title: {title} | "
            f"Source: {source}]\n{content}"
        )
    return "\n\n---\n\n".join(parts)


def _required_setting(name: str, value: str | None) -> str:
    """Return a required configuration value or raise a useful error."""
    if not value or not value.strip():
        raise ValueError(f"{name} must be configured before calling the LLM")
    return value.strip()


def _response_text(value: object, provider: str) -> str:
    """Return plain response text and reject an empty provider completion."""
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        raise RuntimeError(f"{provider} returned an empty response")
    return text


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    # TODO: Dispatch theo LLM_PROVIDER.
    #
    # - openai    -> OPENAI_API_KEY
    # - gemini    -> GEMINI_API_KEY
    # - anthropic -> ANTHROPIC_API_KEY
    #
    # Dùng LLM_MODEL và trả về text thuần cho cả ba nhánh.
    provider = _required_setting("LLM_PROVIDER", LLM_PROVIDER).lower()
    model = _required_setting("LLM_MODEL", LLM_MODEL)

    # Keep SDK imports local: formatting/evaluation can use this module even
    # when optional provider packages are unavailable, and no client is made
    # until this function is explicitly called.
    if provider == "openai":
        api_key = _required_setting("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        from openai import OpenAI

        response = OpenAI(api_key=api_key).chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return _response_text(response.choices[0].message.content, provider)

    if provider == "gemini":
        api_key = _required_setting("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
        from google import genai
        from google.genai import types

        response = genai.Client(api_key=api_key).models.generate_content(
            model=model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=TEMPERATURE,
                top_p=TOP_P,
            ),
        )
        return _response_text(response.text, provider)

    if provider == "anthropic":
        api_key = _required_setting(
            "ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY")
        )
        from anthropic import Anthropic

        response = Anthropic(api_key=api_key).messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        text = "".join(
            block.text
            for block in response.content
            if isinstance(getattr(block, "text", None), str)
        )
        return _response_text(text, provider)

    raise ValueError(
        "LLM_PROVIDER must be one of: openai, gemini, anthropic "
        f"(received {provider!r})"
    )


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    # TODO: Implement end-to-end generation.
    #
    # chunks = retrieve(query, top_k=top_k)
    # if not chunks:
    #     return {
    #         "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
    #         "sources": [],
    #         "retrieval_source": "none",
    #     }
    # reordered = reorder_for_llm(chunks)
    # context = format_context(reordered)
    # user_message = f"Context:\n{context}\n\nQuestion: {query}"
    # answer = call_llm(SYSTEM_PROMPT, user_message)
    # return {
    #     "answer": answer,
    #     "sources": chunks,
    #     "retrieval_source": chunks[0]["retrieval_method"],
    # }
    raise NotImplementedError("Implement generate_with_citation")


if __name__ == "__main__":
    print(generate_with_citation("test query"))
