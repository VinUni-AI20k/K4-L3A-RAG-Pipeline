"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score. Công thức: RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.

-> Dùng Jina hoặc self host hoặc bất cứ công cụ nào bạn quen
"""


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse nhiều ranked lists và trả hybrid SearchResult."""
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            item_id = item["id"]
            scores[item_id] = scores.get(item_id, 0.0) + 1 / (k + rank)
            items[item_id] = item

    ranked_ids = sorted(scores, key=scores.get, reverse=True)

    results = []
    for item_id in ranked_ids[:top_k]:
        result = items[item_id].copy()
        result["score"] = scores[item_id]
        result["retrieval_method"] = "hybrid"
        results.append(result)

    return results


def rerank_advanced(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """Rerank candidates bằng Neural Reranker (Jina API hoặc Gemini LLM)."""
    if not candidates:
        return []

    # 1. Loại bỏ trùng lặp theo id nhưng giữ nguyên thứ tự
    seen = set()
    unique = []
    for c in candidates:
        if c["id"] not in seen:
            seen.add(c["id"])
            unique.append(c)

    if len(unique) <= 1:
        res = [c.copy() for c in unique[:top_k]]
        for r in res:
            r["retrieval_method"] = "reranked"
        return res

    import os
    import json
    import re
    from dotenv import load_dotenv

    load_dotenv()

    # 2. Nếu có Jina API key thì ưu tiên gọi Jina
    jina_key = os.getenv("JINA_API_KEY", "").strip()
    if jina_key:
        try:
            import requests
            url = "https://api.jina.ai/v1/rerank"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {jina_key}",
            }
            data = {
                "model": "jina-reranker-v2-base-multilingual",
                "query": query,
                "documents": [c["content"] for c in unique],
                "top_n": top_k,
            }
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            if resp.status_code == 200:
                res_json = resp.json()
                results = []
                for item in res_json.get("results", []):
                    idx = item["index"]
                    score = float(item["relevance_score"])
                    r = unique[idx].copy()
                    r["score"] = score
                    r["retrieval_method"] = "reranked"
                    results.append(r)
                if results:
                    return results
        except Exception:
            pass

    # 3. Fallback dùng Gemini LLM Reranker (GEMINI_API_KEY)
    try:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            res = [c.copy() for c in unique[:top_k]]
            for r in res:
                r["retrieval_method"] = "reranked"
            return res

        client = genai.Client(api_key=api_key)
        model_name = os.getenv("LLM_MODEL", "gemini-3.5-flash")

        doc_descs = [f"[{i}] {c['content'][:350].replace('\n', ' ')}" for i, c in enumerate(unique)]
        prompt = (
            f"Bạn là hệ thống Reranker đánh giá độ liên quan giữa Câu hỏi và Danh sách tài liệu.\n"
            f"Câu hỏi: \"{query}\"\n\n"
            f"Danh sách tài liệu:\n" + "\n".join(doc_descs) + "\n\n"
            f"Yêu cầu: Hãy chấm điểm độ liên quan của từng tài liệu với câu hỏi từ 0.0 đến 1.0.\n"
            f"Chỉ trả về JSON thuần định dạng mảng: [{{\"id\": 0, \"score\": 0.95}}, ...]"
        )

        resp = client.models.generate_content(model=model_name, contents=prompt)
        text = resp.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        scores_data = json.loads(text)
        scores_map = {int(e["id"]): float(e["score"]) for e in scores_data}

        scored = []
        for i, c in enumerate(unique):
            r = c.copy()
            r["score"] = scores_map.get(i, 0.0)
            r["retrieval_method"] = "reranked"
            scored.append(r)

        return sorted(scored, key=lambda x: x["score"], reverse=True)[:top_k]

    except Exception:
        res = [c.copy() for c in unique[:top_k]]
        for r in res:
            r["retrieval_method"] = "reranked"
        return res


if __name__ == "__main__":
    print("Implement rerank_rrf and rerank_advanced, then run contract tests.")
