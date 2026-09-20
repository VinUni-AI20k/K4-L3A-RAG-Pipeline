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

SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên viên tư vấn thông tin và chính sách của Vinhomes.
Nhiệm vụ: Trả lời câu hỏi dựa CHÍNH XÁC trên phần Context được cung cấp.

Quy tắc bắt buộc:
1. Chỉ sử dụng dữ liệu trong Context. Tuyệt đối không suy diễn hoặc bịa đặt thông tin.
2. Với mỗi luận điểm quan trọng, hãy ghi rõ trích dẫn nguồn (ví dụ: [Document 1], [Document 2]...).
3. Nếu Context không có đủ thông tin để trả lời câu hỏi, hãy từ chối một cách an toàn bằng câu:
"Tôi không thể xác minh thông tin này từ nguồn hiện có."
4. Trình bày mạch lạc, lịch sự, rõ ràng."""



def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context (chống lost-in-the-middle)."""
    if len(chunks) <= 2:
        return [item.copy() for item in chunks]
    front = [chunks[i] for i in range(0, len(chunks), 2)]
    back = [chunks[i] for i in range(1, len(chunks), 2)]
    return list(front + back[::-1])


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        title = metadata.get("title", "Tài liệu")
        source = metadata.get("source", "Nguồn")
        parts.append(
            f"[Document {index} | Title: {title} | "
            f"Source: {source}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)



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




SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult kèm trích dẫn nguồn và từ chối an toàn."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as e:
        logger.error(f"Generation error across all LLM tiers: {e}")
        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
        }

    if not answer or not answer.strip() or SAFE_REFUSAL.lower() in answer.lower():
        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
        }

    # Contract chỉ chấp nhận 'hybrid' | 'pageindex' | 'none'
    first_method = chunks[0].get("retrieval_method", "hybrid")
    retrieval_source = "pageindex" if first_method == "pageindex" else "hybrid"

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }




if __name__ == "__main__":
    print(generate_with_citation("test query"))
