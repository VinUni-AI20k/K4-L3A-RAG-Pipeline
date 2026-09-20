"""
Task 14 (bonus) — HyDE (Hypothetical Document Embeddings).

Câu hỏi ngắn ("Band 7 Lexical Resource yêu cầu gì?") và chunk band descriptor
("uses a sufficient range of vocabulary to allow some flexibility and
precision...") khác nhau về văn phong nên cosine giữa chúng thấp. HyDE nhờ LLM
viết một đoạn *giả định* trả lời câu hỏi theo đúng văn phong tài liệu, rồi
dùng đoạn đó để tìm kiếm: embedding của đoạn giả định gần chunk thật hơn là
embedding của câu hỏi.

Cách dùng trong Task 9 (HYDE_ENABLED=1):
    text = expand_query(query)            # query + "\\n" + hypothetical
    RRF([dense(query), dense(text), bm25(text)])   # vẫn một lần RRF
Dense trên query gốc được giữ để phòng hypothetical lạc đề; fallback vẫn dùng
cosine của query gốc nên threshold 0.53 không phải hiệu chỉnh lại.

Đoạn giả định có thể chứa thông tin sai — nó chỉ dùng để *tìm*, không bao giờ
đưa vào Context của Task 10, nên không ảnh hưởng faithfulness.

Chạy:
    python -m src.task14_hyde "câu hỏi"    # in đoạn giả định
"""

import os
import re
import sys

from dotenv import load_dotenv


load_dotenv()

HYDE_ENABLED = os.getenv("HYDE_ENABLED", "0").strip().lower() in {"1", "true", "yes"}
MAX_HYPOTHETICAL_CHARS = 700   # ~ một chunk 500 ký tự của Task 4, không để át câu hỏi

# Corpus là tài liệu IELTS tiếng Anh nên đoạn giả định luôn viết tiếng Anh, kể
# cả khi câu hỏi tiếng Việt — đây chính là bước "dịch" câu hỏi sang văn phong
# và ngôn ngữ của tài liệu.
HYDE_PROMPT = """You write a short hypothetical passage that could appear in an official IELTS Writing
document (band descriptors, key assessment criteria, scoring guide, or exam guidance) and that
would directly answer the user's question.
Rules:
- Write in English, 2-4 sentences, at most 80 words.
- Use the vocabulary of IELTS band descriptors (e.g. Task Achievement, Task Response, Coherence and
  Cohesion, Lexical Resource, Grammatical Range and Accuracy, band numbers, word counts).
- Do not mention that it is hypothetical, do not address the user, no preamble.
Output only the passage."""


def generate_hypothetical(query: str) -> str:
    """Đoạn giả định trả lời ``query``; lỗi LLM thì trả chuỗi rỗng."""
    if not query.strip():
        return ""
    # Import trễ: task10 import task9, task9 import module này — tránh vòng.
    from .task10_generation import call_llm

    try:
        text = call_llm(HYDE_PROMPT, f"Question: {query}")
    except Exception:  # noqa: BLE001 - HyDE là tiện ích, không được chặn retrieval
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_HYPOTHETICAL_CHARS]


def expand_query(query: str) -> str:
    """Query gốc nối với đoạn giả định; không có đoạn giả định thì trả query."""
    hypothetical = generate_hypothetical(query)
    return f"{query}\n{hypothetical}" if hypothetical else query


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What does Band 7 require for Lexical Resource in Writing Task 2?"
    print(f"Query: {question}\n")
    print(generate_hypothetical(question))
