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
Mỗi khẳng định phải có citation [Document X]. Nếu thiếu evidence, hãy từ chối xác minh."""

SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context."""
    if len(chunks) <= 2:
        return [chunk.copy() for chunk in chunks]
    front = chunks[::2]
    back = chunks[1::2]
    return [chunk.copy() for chunk in front + back[::-1]]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        title = metadata.get("title", "Tài liệu")
        source = metadata.get("source", "Nguồn")
        parts.append(
            f"[Document {index} | Title: {title} | "
            f"Source: {source}]\n{chunk.get('content', '')}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    model = os.getenv("LLM_MODEL", "")

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return SAFE_REFUSAL
        from google import genai
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=model or "gemini-2.5-flash",
            contents=user_message,
            config={"system_instruction": system_prompt, "temperature": TEMPERATURE},
        )
        return (resp.text or "").strip()

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return SAFE_REFUSAL
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
        )
        return resp.choices[0].message.content.strip()

    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return SAFE_REFUSAL
        import anthropic
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        resp = client.messages.create(
            model=model or "claude-3-5-haiku-20241022",
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=1024,
            temperature=TEMPERATURE,
        )
        return resp.content[0].text.strip()

    return SAFE_REFUSAL


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    if not query or not query.strip():
        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
        }

    try:
        chunks = retrieve(query, top_k=top_k)
    except Exception:
        chunks = []

    if not chunks:
        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = (
        f"Context:\n{context}\n\n"
        f"Question: {query}\n\n"
        f"Dựa trên các đoạn tài liệu được cung cấp ở trên, hãy trả lời câu hỏi và "
        f"trích dẫn rõ [Document X] tương ứng cho từng thông tin. "
        f"Nếu các tài liệu không chứa đủ căn cứ trả lời, hãy trả lời chính xác: '{SAFE_REFUSAL}'."
    )

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception:
        answer = SAFE_REFUSAL

    if not answer or not answer.strip():
        answer = SAFE_REFUSAL

    raw_method = chunks[0].get("retrieval_method", "hybrid")
    retrieval_source = raw_method if raw_method in {"hybrid", "pageindex"} else "hybrid"

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }


if __name__ == "__main__":
    print(generate_with_citation("test query"))
