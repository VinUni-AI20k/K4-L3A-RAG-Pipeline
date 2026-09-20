"""Task 10 ? Generation c? citation.

H??ng d?n:
    1. Retrieve top-k chunks.
    2. Reorder ?? gi?m lost-in-the-middle.
    3. Format context k?m title v? source.
    4. G?i provider ???c ch?n trong .env.
    5. Tr? answer, sources v? retrieval_source.

N?u context kh?ng ?? ho?c provider l?i, tr? safe refusal; kh?ng b?a th?ng tin.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from .contracts import validate_generation_result
from .task9_retrieval_pipeline import retrieve

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip() or (
    "gemini-2.0-flash" if LLM_PROVIDER == "gemini" else ""
)

SYSTEM_PROMPT = """B?n l? tr? l? tr? l?i t? ngu?n t?i li?u ???c cung c?p.
Ch? d?ng CONTEXT. M?i kh?ng ??nh ph?i c? citation [Document X].
N?u CONTEXT kh?ng ?? th?ng tin, h?y t? ch?i x?c minh v? kh?ng b?a th?ng tin."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """??a chunks quan tr?ng v? ??u v? cu?i context."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """T?o context c? title v? source label."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        title = metadata.get("title", "Unknown")
        source = metadata.get("source", "Unknown")
        parts.append(
            f"[Document {index} | Title: {title} | Source: {source}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """G?i OpenAI, Gemini ho?c Anthropic theo c?u h?nh."""
    if LLM_PROVIDER == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content or ""

    if LLM_PROVIDER == "gemini":
        from google import genai
        from google.genai import types as genai_types

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        model_name = os.getenv("LLM_MODEL") or "gemini-2.0-flash"
        config = genai_types.GenerateContentConfig(
            temperature=TEMPERATURE,
            top_p=TOP_P,
            system_instruction=system_prompt,
        )
        response = client.models.generate_content(
            model=model_name,
            contents=user_message,
            config=config,
        )
        return response.text or ""

    if LLM_PROVIDER == "anthropic":
        from anthropic import Anthropic

        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        model = os.getenv("LLM_MODEL", "claude-3-haiku-20240307")
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Tr? v? GenerationResult."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        result = {
            "answer": "T?i kh?ng th? x?c minh th?ng tin n?y t? ngu?n hi?n c?.",
            "sources": [],
            "retrieval_source": "none",
        }
        validate_generation_result(result)
        return result

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"CONTEXT:\n{context}\n\nQUESTION: {query}"

    retrieval_source = (
        "pageindex" if reordered[0].get("retrieval_method") == "pageindex" else "hybrid"
    )

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:
        print(f"LLM error: {type(error).__name__}: {error}")
        sources = sorted(reordered, key=lambda item: item.get("score", 0.0), reverse=True)
        result = {
            "answer": "T?i kh?ng th? x?c minh th?ng tin n?y t? ngu?n hi?n c?.",
            "sources": sources,
            "retrieval_source": retrieval_source,
        }
        validate_generation_result(result)
        return result

    # Context ?? ???c reorder ?? gi?m lost-in-the-middle. Ri?ng `sources`
    # ph?i ???c s?p theo score gi?m d?n theo SearchResult contract.
    sources = sorted(reordered, key=lambda item: item.get("score", 0.0), reverse=True)

    result = {
        "answer": answer or "T?i kh?ng th? x?c minh th?ng tin n?y t? ngu?n hi?n c?.",
        "sources": sources,
        "retrieval_source": retrieval_source,
    }
    validate_generation_result(result)
    return result


if __name__ == "__main__":
    result = generate_with_citation("Quy ??nh visa Vi?t Nam c? th?i h?n bao l?u?", top_k=3)
    print(result["retrieval_source"])
    print(result["answer"])
    print("sources:", len(result["sources"]))
