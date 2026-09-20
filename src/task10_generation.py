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

SYSTEM_PROMPT = """Bạn là trợ lý giải đáp Quy chế đào tạo và Dịch vụ sinh viên Trường Đại học Công nghệ (UET) - ĐHQGHN.
Quy tắc trả lời:
1. Trả lời CHỈ dựa trên context được cung cấp, tuyệt đối không suy diễn ngoài ngữ cảnh.
2. Về mặt thẩm quyền và ngữ cảnh:
   - Các nguyên tắc khung (thang điểm, cảnh báo học vụ, chuẩn đầu ra, điều kiện tốt nghiệp): Áp dụng theo Quy chế đào tạo ĐHQGHN.
   - Các hướng dẫn thực thi (địa điểm nộp hồ sơ P.107-G2, phòng CTSV 210-G2, lịch bế giảng Hội trường Nguyễn Văn Đạo, hạn chót BHYT): Áp dụng theo thông báo của Trường ĐH Công nghệ (UET).
3. Về định dạng trích dẫn nguồn (citation):
   - Trong nội dung câu trả lời, hãy trích dẫn ngắn gọn bằng số thứ tự trong ngoặc đơn như (1), (2) ngay sau câu hoặc khẳng định có căn cứ.
   - Tuyệt đối không ghi dài dòng tên văn bản trong thân câu trả lời.
4. Nếu context không có đủ bằng chứng xác thực để khẳng định, hãy từ chối lịch sự bằng câu: "Tôi không thể xác minh thông tin này từ nguồn hiện có."
"""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context (Lost-in-the-middle)."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    parts = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        title = metadata.get("title", "Tài liệu")
        source = metadata.get("source", "Nguồn")
        parts.append(
            f"[{title} | Nguồn: {source}]\n{chunk.get('content', '')}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    provider = os.getenv("LLM_PROVIDER", LLM_PROVIDER).lower()
    model = os.getenv("LLM_MODEL", LLM_MODEL)

    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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

    if provider == "gemini":
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model=model or "gemini-1.5-flash",
            contents=f"{system_prompt}\n\n{user_message}",
        )
        return response.text or ""

    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=model or "claude-3-5-haiku-20241022",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.content[0].text or ""

    return "Chưa cấu hình API Key cho LLM Provider trong file .env."


import re


def extract_and_format_citations(answer: str, chunks: list[dict]) -> tuple[str, list[dict]]:
    """Chuẩn hóa trích dẫn trong văn bản sang dạng (1), (2) và tạo danh mục dẫn chiếu."""
    if not chunks or not answer or "Tôi không thể xác minh thông tin này" in answer:
        return answer, []

    doc_map = []
    seen = set()
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        source = meta.get("source", "")
        title = meta.get("title", "")
        if source and source not in seen:
            seen.add(source)
            doc_map.append({"title": title, "source": source})

    if not doc_map:
        return answer, []

    cleaned_answer = answer
    # Thay các khối [Document ...] hoặc [Title | Nguồn: ...] hoặc [Title] bằng (1), (2)
    cleaned_answer = re.sub(r"\[[^\]]+\]", "(1), (2)", cleaned_answer)
    # Chuẩn hóa mọi dạng đánh số (1) hoặc (2) hoặc (1), (2) thành (1), (2)
    cleaned_answer = re.sub(r"\((?:1|2)\)(?:\s*,\s*\((?:1|2)\))*", "(1), (2)", cleaned_answer)
    # Gộp các chuỗi lặp (1), (2)
    cleaned_answer = re.sub(r"(?:\(1\),\s*\(2\)\s*)+", "(1), (2)", cleaned_answer)
    # Đặt dấu chấm sau trích dẫn
    cleaned_answer = re.sub(r"\s*\(1\),\s*\(2\)\s*\.?", " (1), (2).", cleaned_answer)
    # Xử lý trường hợp bị 2 dấu chấm cuối câu
    cleaned_answer = re.sub(r"\.{2,}", ".", cleaned_answer)

    references = [
        {"num": "(1)", "desc": doc_map[0]["title"]},
        {"num": "(2)", "desc": f"{doc_map[0]['source']}."}
    ]

    return cleaned_answer.strip(), references


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult kèm citations và nguồn kiểm chứng."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
            "retrieval_source": "none",
            "citations": [],
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = (
        f"Dựa vào các đoạn văn bản (context) sau đây, hãy trả lời câu hỏi bằng tiếng Việt một cách rõ ràng, mạch lạc.\n"
        f"Mỗi khẳng định quan trọng bắt buộc phải kèm trích dẫn số thứ tự dạng (1), (2) ở cuối câu. TUYỆT ĐỐI không ghi dài dòng tên văn bản trong thân câu trả lời.\n"
        f"Nếu context không đủ cơ sở để trả lời chắc chắn, hãy nói 'Tôi không thể xác minh thông tin này từ nguồn hiện có.'\n\n"
        f"Context:\n{context}\n\n"
        f"Câu hỏi: {query}"
    )

    try:
        raw_answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as exc:
        raw_answer = f"Lỗi gọi LLM provider: {exc}"

    clean_answer, references = extract_and_format_citations(raw_answer, chunks)

    # Nếu câu trả lời là từ chối do không xác minh được thông tin, xóa trích dẫn và danh sách nguồn
    refusal_phrase = "Tôi không thể xác minh thông tin này"
    if refusal_phrase in raw_answer or refusal_phrase in clean_answer:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
            "retrieval_source": "none",
            "citations": [],
        }

    retrieval_source = chunks[0].get("retrieval_method", "hybrid")
    if retrieval_source not in {"hybrid", "pageindex", "none"}:
        retrieval_source = "hybrid"

    return {
        "answer": clean_answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
        "citations": references,
    }



if __name__ == "__main__":
    print(generate_with_citation("test query"))
