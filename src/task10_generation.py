"""Generate grounded answers from retrieved chunks with source citations."""

import os
from dotenv import load_dotenv
from .contracts import validate_generation_result
from .task4_chunking_indexing import ROOT
from .task9_retrieval_pipeline import retrieve

load_dotenv(ROOT / ".env")
TOP_K = 5
TOP_P = 0.9
REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
_configured_model = os.getenv("LLM_MODEL", "").strip()
_configured_key = os.getenv("OPENAI_API_KEY", "").strip()
if LLM_PROVIDER == "openai" and not _configured_key and _configured_model.startswith("sk-"):
    OPENAI_API_KEY = _configured_model
    LLM_MODEL = os.getenv("OPENAI_CHAT_MODEL", "o4-mini").strip()
else:
    OPENAI_API_KEY = _configured_key
    LLM_MODEL = _configured_model or "o4-mini"

SYSTEM_PROMPT = """Trả lời chỉ từ context được cung cấp.
Mỗi khẳng định phải có citation dạng [Document N]. Nếu context không đủ,
hãy nói rõ rằng không thể xác minh từ nguồn hiện có; không dùng kiến thức ngoài context."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Distribute high-ranked chunks at the beginning and end of context."""
    if len(chunks) <= 2:
        return list(chunks)
    return list(chunks[::2]) + list(chunks[1::2])[::-1]


def format_context(chunks: list[dict]) -> str:
    """Format context with stable, human-readable document labels."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        page = f" | PDF page: {metadata['pdf_page']}" if metadata.get("pdf_page") else ""
        parts.append(
            f"[Document {index} | Title: {metadata['title']} | "
            f"Source: {metadata['source']}{page}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Call the configured OpenAI model and return plain text."""
    if LLM_PROVIDER != "openai":
        raise RuntimeError(f"LLM_PROVIDER={LLM_PROVIDER!r} chưa được triển khai")
    if not OPENAI_API_KEY:
        raise RuntimeError("Thiếu OPENAI_API_KEY trong .env")
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0, max_retries=2)
    request = {"model": LLM_MODEL, "instructions": system_prompt, "input": user_message}
    # Reasoning models such as o4-mini reject sampling controls like top_p.
    if not LLM_MODEL.lower().startswith(("o1", "o3", "o4")):
        request["top_p"] = TOP_P
    response = client.responses.create(**request)
    text = (response.output_text or "").strip()
    if not text:
        raise RuntimeError("OpenAI không trả về nội dung")
    return text


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Retrieve evidence and generate a cited answer, with safe refusal on failure."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        result = {"answer": REFUSAL, "sources": [], "retrieval_source": "none"}
        validate_generation_result(result)
        return result
    try:
        context = format_context(reorder_for_llm(chunks))
        answer = call_llm(SYSTEM_PROMPT, f"Context:\n{context}\n\nQuestion: {query}")
    except Exception:
        result = {"answer": REFUSAL, "sources": chunks, "retrieval_source": "hybrid"}
        validate_generation_result(result)
        return result
    result = {
        "answer": answer, "sources": chunks,
        "retrieval_source": chunks[0]["retrieval_method"],
    }
    validate_generation_result(result)
    return result


if __name__ == "__main__":
    result = generate_with_citation("Động năng của một vật là gì?", top_k=3)
    print(result["answer"])
    print("Sources:", ", ".join(item["id"] for item in result["sources"]))
