"""Grounded Gemini generation with verifiable numeric citations."""
import os
from dotenv import load_dotenv
from .task9_retrieval_pipeline import retrieve

load_dotenv()
TOP_K, TOP_P, TEMPERATURE = 5, 0.9, 0.2
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ các nguồn hiện có."
SYSTEM_PROMPT = """Bạn là trợ lý du lịch Việt Nam. Chỉ trả lời bằng thông tin trong context.
Viết ngắn gọn bằng tiếng Việt. Sau mỗi khẳng định thực tế, dẫn nguồn bằng [1], [2]...
đúng với số tài liệu trong context. Không dùng kiến thức ngoài. Nếu context không đủ,
chỉ trả lời: Tôi không thể xác minh thông tin này từ các nguồn hiện có."""

def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    if len(chunks) <= 2:
        return list(chunks)
    reordered = [None] * len(chunks)
    positions = list(range(0, len(chunks), 2)) + list(range(1, len(chunks), 2))[::-1]
    for item, position in zip(chunks, positions):
        reordered[position] = item
    return reordered

def format_context(chunks: list[dict]) -> str:
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        parts.append(f"[{index}] Title: {metadata['title']}\nSource: {metadata['source']}\nURL: {metadata.get('url') or 'N/A'}\n{chunk['content']}")
    return "\n\n---\n\n".join(parts)

def call_llm(system_prompt: str, user_message: str) -> str:
    if LLM_PROVIDER != "gemini":
        raise ValueError("LLM_PROVIDER phải là gemini cho dự án này")
    from google import genai
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model=LLM_MODEL, contents=user_message,
        config={"system_instruction": system_prompt, "temperature": TEMPERATURE,
                "top_p": TOP_P, "max_output_tokens": 1024})
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty response")
    return text

def generate_with_citation(query: str, top_k: int = TOP_K, score_threshold: float = 0.82, use_reranking: bool = True, **kwargs) -> dict:
    if not query.strip():
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}
    try:
        chunks = retrieve(query, top_k=top_k, score_threshold=score_threshold, use_reranking=use_reranking)
        if not chunks:
            return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}
        reordered = reorder_for_llm(chunks)
        message = f"Context:\n{format_context(reordered)}\n\nQuestion: {query}"
        answer = call_llm(SYSTEM_PROMPT, message)
        if answer != SAFE_REFUSAL and not any(f"[{i}]" in answer for i in range(1, len(chunks) + 1)):
            answer += "\n\nNguồn tham khảo: " + ", ".join(f"[{i}]" for i in range(1, len(chunks) + 1))
        source_type = chunks[0]["retrieval_method"]
        return {"answer": answer, "sources": reordered,
                "retrieval_source": "pageindex" if source_type == "pageindex" else "hybrid"}
    except Exception:
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

if __name__ == "__main__":
    print(generate_with_citation("Hà Giang mùa nào đẹp?"))
