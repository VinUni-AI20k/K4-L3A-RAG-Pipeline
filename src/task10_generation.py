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
    """Reorder chunks để giảm lost-in-the-middle effect.

    Đặt chunk quan trọng nhất (score cao nhất) ở đầu, các chunk còn lại
    xen kẽ từ hai đầu để thông tin quan trọng không bị chìm ở giữa.
    Không mutate list đầu vào.
    """
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label để LLM tạo citation kiểm chứng được."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        parts.append(
            f"[Document {index} | Title: {meta['title']} | "
            f"Source: {meta['source']}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình LLM_PROVIDER trong .env."""
    provider = LLM_PROVIDER.strip().lower()

    if provider == "openai":
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_PROVIDER=openai nhưng thiếu OPENAI_API_KEY trong .env")
        model = LLM_MODEL or "gpt-4o-mini"
        client = OpenAI(api_key=api_key)
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

    if provider == "gemini":
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_PROVIDER=gemini nhưng thiếu GEMINI_API_KEY trong .env")
        model = LLM_MODEL or "gemini-2.0-flash"
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=f"{system_prompt}\n\n{user_message}",
        )
        return response.text or ""

    if provider == "anthropic":
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_PROVIDER=anthropic nhưng thiếu ANTHROPIC_API_KEY trong .env")
        model = LLM_MODEL or "claude-3-5-haiku-latest"
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return message.content[0].text or ""

    raise ValueError(f"LLM_PROVIDER không hỗ trợ: '{provider}'. Chọn openai, gemini hoặc anthropic.")


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Retrieve, reorder, format context và sinh câu trả lời có citation.

    Returns:
        GenerationResult với answer, sources và retrieval_source.
        Trả safe refusal nếu không có chunk hoặc provider lỗi.
    """
    chunks = retrieve(query, top_k=top_k)

    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
            "retrieval_source": "none",
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nCâu hỏi: {query}"

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as exc:
        print(f"[task10] LLM lỗi: {exc}")
        answer = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

    retrieval_source = chunks[0].get("retrieval_method", "none")
    # Map retrieval_method sang retrieval_source hợp lệ theo contract.
    if retrieval_source not in ("hybrid", "pageindex"):
        retrieval_source = "hybrid"

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }


if __name__ == "__main__":
    print(generate_with_citation("test query"))
