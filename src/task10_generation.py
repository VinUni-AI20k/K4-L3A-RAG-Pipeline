"""
Task 10 — Generation có citation cho trợ lý pháp luật về Pod & Chất cấm.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title, source và ID bằng chứng [E1], [E2]...
    4. Dispatch provider theo .env (Gemini, OpenAI, Anthropic).
    5. Kiểm chứng citation và trả về GenerationResult chuẩn contract.
"""

import os
from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve

load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "gemini").lower().strip()
LLM_MODEL = os.getenv("LLM_MODEL") or ("gemini-3.5-flash-lite" if LLM_PROVIDER == "gemini" else "gpt-4o-mini")

SYSTEM_PROMPT = """Bạn là trợ lý tư vấn pháp lý chuyên sâu tại Việt Nam về thuốc lá điện tử (pod, vape) và các chất ma túy / tiền chất bị cấm.
Hãy trả lời câu hỏi của người dùng một cách chính xác, khách quan, hoàn toàn dựa trên các bằng chứng (Evidence) được cung cấp.

Quy tắc trích dẫn bắt buộc:
1. Mọi khẳng định thực tế, căn cứ pháp lý, điều luật, mức xử phạt hành chính hoặc chế tài hình sự phải có trích dẫn ID bằng chứng tương ứng trong ngoặc vuông, ví dụ: [E1] hoặc [E1], [E2].
2. Tuyệt đối không tự bịa đặt ID bằng chứng (chỉ dùng các ID [E1], [E2]... xuất hiện trong bằng chứng).
3. Tuyệt đối không tự bịa đặt điều luật, số nghị định hoặc mức phạt không có trong bằng chứng.
4. Nếu tài liệu không đủ thông tin để trả lời câu hỏi, hãy từ chối lịch sự bằng câu: "Tôi không thể xác minh thông tin này từ nguồn hiện có."
"""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context để giảm hiện tượng lost-in-the-middle."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title, source label và evidence ID [E1], [E2]..."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        title = metadata.get("title") or "Tài liệu"
        source = metadata.get("source") or "Văn bản"
        doc_type = metadata.get("doc_type", "document")
        url = metadata.get("url") or "N/A"

        header_lines = [
            f"[E{index}] Title: {title} | Source: {source} | Type: {doc_type}",
        ]
        if doc_type == "legal":
            start = metadata.get("page_start")
            end = metadata.get("page_end")
            pages = str(start) if (start and start == end) else f"{start}–{end}" if start else "N/A"
            legal_path = metadata.get("legal_path") or "N/A"
            issuer = metadata.get("issuer") or source
            header_lines.append(f"Issuer: {issuer} | Legal path: {legal_path} | Pages: {pages}")
        else:
            publisher = metadata.get("publisher") or source
            pub_date = metadata.get("published_date") or "N/A"
            header_lines.append(f"Publisher: {publisher} | Published: {pub_date}")

        header_lines.append(f"URL: {url}")
        content = chunk.get("content", "")
        parts.append("\n".join(header_lines) + f"\nContent:\n{content}")
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi LLM theo provider được cấu hình trong .env (Gemini, OpenAI, Anthropic)."""
    provider = (os.getenv("LLM_PROVIDER") or "gemini").lower().strip()
    model = os.getenv("LLM_MODEL") or ""

    if provider == "gemini":
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required in .env")

        client = genai.Client(api_key=api_key)
        model_name = model or "gemini-3.5-flash-lite"
        response = client.models.generate_content(
            model=model_name,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=TEMPERATURE,
                top_p=TOP_P,
            ),
        )
        return response.text or ""

    elif provider == "openai":
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required in .env")

        client = OpenAI(api_key=api_key)
        model_name = model or "gpt-4o-mini"
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.choices[0].message.content or ""

    elif provider == "anthropic":
        from anthropic import Anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required in .env")

        client = Anthropic(api_key=api_key)
        model_name = model or "claude-3-5-haiku-latest"
        response = client.messages.create(
            model=model_name,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
            max_tokens=2048,
        )
        return response.content[0].text or ""

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult với trích dẫn có thể kiểm chứng."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
            "retrieval_source": "none",
        }

    ordered = reorder_for_llm(chunks)
    context_text = format_context(ordered)
    user_prompt = f"Evidence:\n{context_text}\n\nQuestion: {query}"

    try:
        raw_answer = call_llm(SYSTEM_PROMPT, user_prompt)
    except Exception:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
            "retrieval_source": "none",
        }

    # Validate citations
    try:
        from .citations import validate_citations
        validation = validate_citations(raw_answer, ordered)
        if not validation.get("valid", True):
            answer = "Tôi không thể xác minh câu trả lời vì citation do mô hình tạo không hợp lệ."
        else:
            answer = raw_answer
    except Exception:
        answer = raw_answer

    method = chunks[0].get("retrieval_method", "hybrid")
    if method not in {"hybrid", "pageindex"}:
        method = "hybrid"

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": method,
    }


if __name__ == "__main__":
    print(generate_with_citation("test query"))
