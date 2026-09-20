"""
Bonus — HyDE (query expansion) và LLM reranker, so sánh với RRF thường.

Tách riêng khỏi task5-9 để không đụng contract/signature đã bị test khóa cứng
(tests/test_contracts.py::test_public_function_signatures_are_stable). File này
chỉ dùng cho evaluation bonus, không phải một phần bắt buộc của pipeline chính.

  - HyDE: sinh một "câu trả lời giả định" cho câu hỏi bằng LLM, rồi dùng chính
    văn bản đó (thay vì câu hỏi gốc) để embed + dense search — ý tưởng: câu trả
    lời giả định gần với văn phong/nội dung của chunk luật thật hơn là câu hỏi
    ngắn gọn của người dùng.
  - LLM reranker: lấy top-N ứng viên sau RRF, nhờ LLM chấm điểm độ liên quan
    0-10 cho từng đoạn rồi sắp xếp lại — so với RRF (chỉ dựa vào thứ hạng, không
    "đọc hiểu" nội dung).
"""

import os
import re

from dotenv import load_dotenv

from .task4_chunking_indexing import embed_texts, get_collection
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task9_retrieval_pipeline import retrieve

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "") or "gpt-4o-mini"


def _call_openai(system_prompt: str, user_message: str) -> str:
    """LLM call tối giản, chỉ hỗ trợ OpenAI (đủ dùng cho bonus experiment)."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content or ""


HYDE_PROMPT = """Bạn đang viết một đoạn trích giả định (khoảng 3-4 câu) trông như
trích từ một văn bản luật hoặc bài báo tiếng Việt, trả lời cho câu hỏi được đưa
ra. Viết như văn phong pháp lý/báo chí thật, có thể chứa thông tin không chính
xác 100% — mục đích chỉ để tạo văn bản gần nghĩa với câu trả lời thật, không
phải để người dùng đọc. Chỉ trả về đoạn văn, không giải thích thêm."""


def generate_hypothetical_document(query: str) -> str:
    """HyDE: sinh 'câu trả lời giả định' để embed thay cho câu hỏi gốc."""
    try:
        doc = _call_openai(HYDE_PROMPT, query)
        return doc.strip() or query
    except Exception as error:
        print(f"HyDE generation failed: {error}")
        return query


def semantic_search_hyde(query: str, top_k: int = 10) -> list[dict]:
    """Dense search nhưng embed hypothetical document thay vì câu hỏi gốc."""
    hypothetical = generate_hypothetical_document(query)
    query_vector = embed_texts([hypothetical])[0]
    response = get_collection().query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    results = []
    if response and response.get("ids") and response["ids"] and response["ids"][0]:
        for item_id, content, metadata, distance in zip(
            response["ids"][0],
            response["documents"][0],
            response["metadatas"][0],
            response["distances"][0],
        ):
            results.append({
                "id": item_id,
                "content": content,
                "score": max(0.0, 1.0 - float(distance)),
                "metadata": metadata,
                "retrieval_method": "dense",
            })
    return sorted(results, key=lambda item: item["score"], reverse=True)[: max(top_k, 0)]


def retrieve_hyde(query: str, top_k: int = 5) -> list[dict]:
    """Pipeline hybrid nhưng dùng semantic_search_hyde() thay vì semantic_search()."""
    dense = semantic_search_hyde(query, top_k=top_k * 2)
    sparse = lexical_search(query, top_k=top_k * 2)
    fused = rerank_rrf([dense, sparse], top_k=top_k)
    return fused if fused else dense[:top_k]


RERANK_PROMPT = """Chấm điểm mức độ liên quan của đoạn văn bản với câu hỏi, theo
thang 0-10 (0 = hoàn toàn không liên quan, 10 = trả lời trực tiếp câu hỏi).
Chỉ trả về một số nguyên, không giải thích gì thêm."""


def llm_rerank(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """Rerank lại candidates bằng LLM chấm điểm từng đoạn (thay cho RRF)."""
    scored = []
    for item in candidates:
        try:
            raw = _call_openai(RERANK_PROMPT, f"Câu hỏi: {query}\n\nĐoạn văn bản:\n{item['content'][:800]}")
            match = re.search(r"\d+", raw)
            score = float(match.group()) if match else 0.0
        except Exception as error:
            print(f"LLM rerank failed for {item['id']}: {error}")
            score = 0.0
        scored.append({**item, "score": score, "retrieval_method": "hybrid"})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[: max(top_k, 0)]


def retrieve_llm_reranked(query: str, top_k: int = 5, pool_size: int = 10) -> list[dict]:
    """Lấy pool ứng viên từ pipeline hybrid RRF hiện có, rồi rerank lại bằng LLM."""
    pool = retrieve(query, top_k=pool_size, use_reranking=True)
    if not pool:
        return []
    return llm_rerank(query, pool, top_k=top_k)
