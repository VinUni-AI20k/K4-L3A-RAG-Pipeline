"""
Task 10 — Generation có citation và hỗ trợ Conversation Memory.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
Hỗ trợ mở rộng: Multi-turn conversation memory cho câu hỏi nối tiếp.
"""

import os
import re

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "")

SYSTEM_PROMPT = """Bạn là trợ lý pháp lý chuyên nghiệp hỗ trợ tra cứu và giải đáp thông tin quy định pháp luật và tái cơ cấu doanh nghiệp.

QUY TẮC BẮT BUỘC:
1. CHỈ sử dụng thông tin được cung cấp trong phần Context dưới đây. Tuyệt đối KHÔNG sử dụng kiến thức bên ngoài, không tự suy diễn hoặc bịa đặt thông tin.
2. Mọi thông tin, khẳng định hoặc số liệu nêu ra BẮT BUỘC phải kèm theo trích dẫn nguồn chuẩn dạng [Document X] (ví dụ: [Document 1], [Document 2]) tương ứng với tài liệu trong Context.
3. Nếu Context không chứa đủ thông tin để trả lời câu hỏi, bạn PHẢI từ chối trả lời bằng cách nói chính xác: "Tôi không thể xác minh thông tin này từ nguồn hiện có."
4. Trả lời rõ ràng, mạch lạc, trung thực và chuẩn xác với căn cứ pháp lý."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context (giải quyết lost-in-the-middle)."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label chuẩn hóa."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        title = metadata.get("title", "Tài liệu")
        source = metadata.get("source", "Không rõ nguồn")
        parts.append(
            f"[Document {index} | Title: {title} | Source: {source}]\n{chunk.get('content', '')}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    provider = LLM_PROVIDER.lower()
    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = LLM_MODEL or "gpt-4o-mini"
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.choices[0].message.content or ""
    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        model_name = LLM_MODEL or "gemini-2.5-flash"
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
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
        except ImportError:
            import google.generativeai as legacy_genai

            legacy_genai.configure(api_key=api_key)
            model = legacy_genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt,
            )
            response = model.generate_content(
                user_message,
                generation_config={"temperature": TEMPERATURE, "top_p": TOP_P},
            )
            return response.text or ""
    elif provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        model = LLM_MODEL or "claude-3-5-haiku-20241022"
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
            top_p=TOP_P,
            max_tokens=1024,
        )
        return response.content[0].text or ""
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def rewrite_query_for_followup(query: str, history: list[dict]) -> str:
    """Tự động bổ sung ngữ cảnh từ lịch sử chat gần nhất cho câu hỏi nối tiếp."""
    if not history:
        return query

    # Lấy tối đa 2 lượt hỏi-đáp gần nhất
    recent_turns = []
    for msg in history[-4:]:
        role = "Người dùng" if msg.get("role") == "user" else "Trợ lý"
        content = msg.get("content", "")[:300]
        recent_turns.append(f"{role}: {content}")

    context_str = "\n".join(recent_turns)
    rewrite_prompt = (
        "Dựa vào lịch sử cuộc trò chuyện dưới đây, nếu câu hỏi của người dùng là câu hỏi nối tiếp "
        "(sử dụng đại từ thay thế như 'nó', 'đơn vị này', 'quy định đó' hoặc thiếu chủ ngữ), hãy viết lại thành "
        "MỘT câu truy vấn độc lập, đầy đủ ngữ cảnh để tìm kiếm thông tin pháp lý. "
        "Nếu câu hỏi đã đầy đủ ý nghĩa độc lập, chỉ cần trả lại nguyên văn câu hỏi. "
        "Chỉ trả lời duy nhất câu truy vấn viết lại, không thêm lời giải thích nào khác.\n\n"
        f"Lịch sử:\n{context_str}\n\n"
        f"Câu hỏi hiện tại: {query}\n\n"
        "Câu truy vấn độc lập:"
    )
    try:
        rewritten = call_llm(
            "Bạn là bộ tiền xử lý câu hỏi người dùng cho hệ thống tìm kiếm.",
            rewrite_prompt,
        ).strip()
        return rewritten if rewritten else query
    except Exception:
        return query


def generate_with_history(
    query: str,
    history: list[dict] | None = None,
    top_k: int = TOP_K,
) -> dict:
    """Sinh câu trả lời có citation, hỗ trợ multi-turn conversation memory."""
    search_query = query
    if history:
        search_query = rewrite_query_for_followup(query, history)

    chunks = retrieve(search_query, top_k=top_k)
    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
            "retrieval_source": "none",
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)

    history_context = ""
    if history:
        prev_lines = []
        for msg in history[-4:]:
            role = "User" if msg.get("role") == "user" else "Assistant"
            prev_lines.append(f"{role}: {msg.get('content', '')}")
        history_context = "Lịch sử trò chuyện trước đó:\n" + "\n".join(prev_lines) + "\n\n"

    user_message = f"{history_context}Context:\n{context}\n\nQuestion: {query}"

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as e:
        answer = f"Tôi không thể xác minh thông tin này từ nguồn hiện có do lỗi kỹ thuật: {e}"

    # Kiểm tra safe refusal
    refusal_keywords = [
        "không thể xác minh thông tin này từ nguồn hiện có",
        "tôi không thể xác minh",
        "thiếu evidence",
        "không có thông tin",
        "không tìm thấy thông tin",
        "không được đề cập",
        "từ chối xác minh",
        "không thể trả lời",
    ]
    lowered_answer = answer.lower()
    has_refusal_kw = any(kw in lowered_answer for kw in refusal_keywords)
    has_citation = bool(re.search(r"\[document\s*\d+\]|\(document\s*\d+\)", lowered_answer))

    if has_refusal_kw and not has_citation:
        return {
            "answer": answer,
            "sources": [],
            "retrieval_source": "none",
        }

    raw_method = chunks[0].get("retrieval_method", "hybrid")
    retrieval_source = raw_method if raw_method in {"hybrid", "pageindex", "none"} else "hybrid"

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult chuẩn hợp đồng (chữ ký cố định query, top_k)."""
    return generate_with_history(query, history=None, top_k=top_k)


if __name__ == "__main__":
    test_q = "VAMC có số vốn điều lệ là bao nhiêu và do ai quản lý?"
    print(f"=== Query: '{test_q}' ===")
    res = generate_with_citation(test_q, top_k=3)
    print("\n[Answer]:")
    print(res["answer"])
    print(f"\n[Retrieval Source]: {res['retrieval_source']}")
    print(f"[Number of Sources]: {len(res['sources'])}")
