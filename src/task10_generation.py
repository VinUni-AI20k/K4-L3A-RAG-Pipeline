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
    #
    # if len(chunks) <= 2:
    #     return list(chunks)
    # front = chunks[::2]
    # back = chunks[1::2]
    # return front + back[::-1]
    raise NotImplementedError("Implement reorder_for_llm")


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
    raise NotImplementedError("Implement format_context")


import logging

logger = logging.getLogger(__name__)


def _invoke_single_llm(provider: str, model: str, system_prompt: str, user_message: str) -> str:
    """Gọi một provider LLM cụ thể (OpenAI, Gemini, NVIDIA NIM, hoặc Anthropic)."""
    prov = (provider or "").strip().lower()

    if prov in ("openai", "openai_compatible"):
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        base_url = os.getenv("OPENAI_BASE_URL") or None
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.choices[0].message.content or ""

    elif prov == "gemini":
        from google import genai
        from google.genai import types
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        response = client.models.generate_content(
            model=model or "gemini-2.5-flash",
            contents=user_message,
            config=config,
        )
        return response.text or ""

    elif prov == "nvidia":
        from openai import OpenAI
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_API_KEY is not set.")
        base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model or "meta/llama-3.1-70b-instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.choices[0].message.content or ""

    elif prov == "anthropic":
        from anthropic import Anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set.")
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model or "claude-3-5-haiku-latest",
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
            top_p=TOP_P,
            max_tokens=1024,
        )
        return response.content[0].text if response.content else ""

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi LLM với 2 tầng Fallback tự động khi có lỗi."""
    primary_prov = os.getenv("LLM_PROVIDER", "openai")
    primary_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    enable_fallback = os.getenv("ENABLE_LLM_FALLBACK", "true").lower() in ("true", "1", "yes")

    candidates = [(primary_prov, primary_model, "Primary LLM")]

    if enable_fallback:
        fb1_prov = os.getenv("LLM_FALLBACK_PROVIDER_1")
        fb1_model = os.getenv("LLM_FALLBACK_MODEL_1")
        if fb1_prov:
            candidates.append((fb1_prov, fb1_model, "Fallback 1"))

        fb2_prov = os.getenv("LLM_FALLBACK_PROVIDER_2")
        fb2_model = os.getenv("LLM_FALLBACK_MODEL_2")
        if fb2_prov:
            candidates.append((fb2_prov, fb2_model, "Fallback 2"))

    last_error = None
    for index, (prov, mdl, label) in enumerate(candidates):
        try:
            return _invoke_single_llm(prov, mdl, system_prompt, user_message)
        except Exception as e:
            last_error = e
            logger.warning(
                f"[LLM FALLBACK] {label} ({prov} - {mdl}) failed: {e}."
                + (f" Trying next tier..." if index < len(candidates) - 1 else " No more fallbacks.")
            )

    raise RuntimeError(f"All LLM tiers failed. Last error: {last_error}")




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
