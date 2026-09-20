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

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve


load_dotenv(Path(__file__).parent.parent / ".env")

LOGGER = logging.getLogger(__name__)

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()

SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

SYSTEM_PROMPT = """Bạn là trợ lý tra cứu du lịch và di sản Việt Nam.
Chỉ trả lời bằng thông tin trong context được cung cấp.
Mỗi khẳng định thực tế phải có citation dạng [Document N].
Không dùng kiến thức bên ngoài, không suy đoán và không bịa nguồn.
Nếu context không đủ evidence, hãy trả lời đúng câu:
"Tôi không thể xác minh thông tin này từ nguồn hiện có."
Trả lời bằng tiếng Việt, rõ ràng và ngắn gọn."""


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
        metadata = chunk.get("metadata") or {}
        title = metadata.get("title") or "Unknown"
        source = metadata.get("source") or "Unknown"
        url = metadata.get("url") or "N/A"
        parts.append(
            f"[Document {index}]\n"
            f"Title: {title}\n"
            f"Source: {source}\n"
            f"URL: {url}\n"
            f"Chunk ID: {chunk.get('id', 'Unknown')}\n\n"
            f"{chunk.get('content', '')}"
        )
    return "\n\n---\n\n".join(parts)


def _required_setting(name: str) -> str:
    """Read a non-placeholder ASCII setting without exposing its value."""

    value = os.getenv(name, "").strip()
    lowered = value.casefold()
    placeholder_markers = ("your_", "your-", "paste_", "paste-", "dan_", "dán_")
    if not value or lowered.startswith(placeholder_markers):
        raise RuntimeError(f"{name} is not configured")
    if not value.isascii():
        raise RuntimeError(f"{name} must contain ASCII characters only")
    return value


def _clean_answer(answer: object) -> str:
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("LLM provider returned an empty answer")
    return answer.strip()


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    if not LLM_MODEL:
        raise RuntimeError("LLM_MODEL is not configured")

    if LLM_PROVIDER == "openai":
        from openai import OpenAI

        with OpenAI(api_key=_required_setting("OPENAI_API_KEY")) as client:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=TEMPERATURE,
                top_p=TOP_P,
            )
        return _clean_answer(response.choices[0].message.content)

    if LLM_PROVIDER == "gemini":
        from google import genai
        from google.genai import types

        with genai.Client(api_key=_required_setting("GEMINI_API_KEY")) as client:
            chat = client.chats.create(
                model=LLM_MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                ),
            )
            response = chat.send_message(user_message)
        return _clean_answer(response.text)

    if LLM_PROVIDER == "anthropic":
        from anthropic import Anthropic

        with Anthropic(api_key=_required_setting("ANTHROPIC_API_KEY")) as client:
            response = client.messages.create(
                model=LLM_MODEL,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                max_tokens=1024,
                temperature=TEMPERATURE,
                top_p=TOP_P,
            )
        text_parts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
            and getattr(block, "text", None)
        ]
        return _clean_answer("\n".join(text_parts))

    raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    refusal = {
        "answer": SAFE_REFUSAL,
        "sources": [],
        "retrieval_source": "none",
    }
    query = query.strip()
    if not query or top_k <= 0:
        return refusal

    try:
        chunks = retrieve(query, top_k=top_k)
    except Exception:
        LOGGER.exception("Retrieval failed")
        return refusal
    if not chunks:
        return refusal

    context = format_context(reorder_for_llm(chunks))
    user_message = (
        f"Context:\n{context}\n\n"
        f"Question: {query}\n\n"
        "Hãy trả lời và trích dẫn nguồn theo dạng [Document N]."
    )
    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception:
        LOGGER.exception("LLM generation failed")
        return refusal

    first_method = chunks[0].get("retrieval_method")
    retrieval_source = "pageindex" if first_method == "pageindex" else "hybrid"
    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }


if __name__ == "__main__":
    print(generate_with_citation("test query"))
