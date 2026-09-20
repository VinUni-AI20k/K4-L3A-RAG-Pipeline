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
            f"[Document {index} | ID: {chunk['id']} | "
            f"Title: {metadata['title']} | Source: {metadata['source']}]\n"
            f"{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    provider = LLM_PROVIDER.lower().strip()
    try:
        if provider == "openai":
            from openai import OpenAI

            model = LLM_MODEL or "gpt-4o-mini"
            response = OpenAI().chat.completions.create(
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

            model = LLM_MODEL or "gemini-2.0-flash"
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            response = client.models.generate_content(
                model=model,
                contents=f"{system_prompt}\n\n{user_message}",
            )
            return response.text or ""

        if provider == "anthropic":
            from anthropic import Anthropic

            model = LLM_MODEL or "claude-3-5-haiku-latest"
            response = Anthropic().messages.create(
                model=model,
                max_tokens=800,
                temperature=TEMPERATURE,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return "".join(
                block.text for block in response.content
                if getattr(block, "type", "") == "text"
            )
    except Exception:
        return "Tôi không thể xác minh thông tin này từ nguồn hiện có."

    return "Tôi không thể xác minh thông tin này từ nguồn hiện có."


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
            "retrieval_source": "none",
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = (
        f"Context:\n{context}\n\n"
        f"Question: {query}\n\n"
        "Hãy trả lời ngắn gọn bằng tiếng Việt và ghi citation theo dạng "
        "[Document N] cho từng ý chính."
    )
    answer = call_llm(SYSTEM_PROMPT, user_message).strip()
    if not answer:
        answer = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

    method = chunks[0]["retrieval_method"]
    retrieval_source = "pageindex" if method == "pageindex" else "hybrid"
    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }


if __name__ == "__main__":
    print(generate_with_citation("test query"))
