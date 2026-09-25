"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.

Citation: mỗi chunk được đánh số [n] theo thứ tự trong `sources` (score giảm
dần), kể cả khi vị trí trong context bị reorder, nên [n] trong answer luôn map
về sources[n - 1].
"""

import logging
import os
import re

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve


load_dotenv()
logger = logging.getLogger(__name__)

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3
MAX_OUTPUT_TOKENS = 800

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
    "anthropic": "claude-haiku-4-5",
}
LLM_MODEL = os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(LLM_PROVIDER, "")

REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

SYSTEM_PROMPT = f"""Bạn là trợ lý hỏi đáp về chính sách của sàn TMĐT Shopee Việt Nam.
Quy tắc:
1. Chỉ trả lời dựa trên các đoạn context được cung cấp; không dùng kiến thức bên ngoài.
2. Mỗi câu khẳng định phải có citation dạng [n], trong đó n là số của đoạn context
   chứa bằng chứng (ví dụ: "... trong vòng 15 ngày [2]."). Có thể ghép nhiều nguồn: [1][3].
3. Giữ nguyên số liệu, thời hạn, mức phí đúng như context.
4. Nếu context không chứa đủ thông tin để trả lời, chỉ trả lời đúng một câu:
   "{REFUSAL}"
5. Trả lời bằng tiếng Việt, ngắn gọn, đi thẳng vào câu hỏi."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context (không mutate input).

    Với chunks đã sort giảm dần: [1, 2, 3, 4, 5] → [1, 3, 5, 4, 2].
    """
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict], citation_numbers: dict[str, int] | None = None) -> str:
    """Tạo context có số citation, title và source label."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        number = (citation_numbers or {}).get(chunk["id"], index)
        url = metadata.get("url") or "n/a"
        parts.append(
            f"[{number}] Title: {metadata['title']} | Source: {metadata['source']} | URL: {url}\n"
            f"{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    if LLM_PROVIDER == "openai":
        from openai import OpenAI

        response = OpenAI(timeout=60).chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
        return (response.choices[0].message.content or "").strip()

    if LLM_PROVIDER == "gemini":
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            ),
        )
        return (response.text or "").strip()

    if LLM_PROVIDER == "anthropic":
        from anthropic import Anthropic

        # Claude không cho đặt đồng thời temperature và top_p: chỉ dùng temperature.
        response = Anthropic(timeout=60).messages.create(
            model=LLM_MODEL,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
        return "".join(block.text for block in response.content if block.type == "text").strip()

    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")


def cited_numbers(answer: str) -> list[int]:
    """Các số citation [n] xuất hiện trong answer, theo thứ tự xuất hiện."""
    numbers = []
    for match in re.finditer(r"\[(\d+(?:\s*,\s*\d+)*)\]", answer):
        for value in match.group(1).split(","):
            number = int(value)
            if number not in numbers:
                numbers.append(number)
    return numbers


def _refusal() -> dict:
    return {"answer": REFUSAL, "sources": [], "retrieval_source": "none"}


def generate_answer(query: str, top_k: int = TOP_K, use_reranking: bool = True) -> dict:
    """GenerationResult; use_reranking=False cho cấu hình dense-only (A/B)."""
    if not query.strip():
        return _refusal()
    chunks = retrieve(query, top_k=top_k, use_reranking=use_reranking)
    if not chunks:
        return _refusal()

    citation_numbers = {chunk["id"]: index for index, chunk in enumerate(chunks, 1)}
    context = format_context(reorder_for_llm(chunks), citation_numbers)
    user_message = f"Context:\n{context}\n\nCâu hỏi: {query}"
    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:
        logger.error("LLM provider %s failed: %s", LLM_PROVIDER, error)
        return _refusal()

    if not answer or answer.strip().rstrip(".") == REFUSAL.rstrip("."):
        return _refusal()
    # Bỏ citation trỏ tới nguồn không tồn tại để mọi [n] map được về sources.
    valid = set(range(1, len(chunks) + 1))
    answer = re.sub(
        r"\[(\d+)\]",
        lambda match: match.group(0) if int(match.group(1)) in valid else "",
        answer,
    )
    method = chunks[0]["retrieval_method"]
    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": "pageindex" if method == "pageindex" else "hybrid",
    }


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    return generate_answer(query, top_k=top_k)


if __name__ == "__main__":
    result = generate_with_citation("Người mua có bao nhiêu ngày để yêu cầu trả hàng?")
    print(result["answer"])
    for number, source in enumerate(result["sources"], 1):
        print(f"[{number}] {source['metadata']['title']} — {source['id']}")
