"""Reproducible Gemini-judged A/B evaluation for dense versus hybrid retrieval."""
import json
import hashlib
import re
import time
from pathlib import Path
from src.task5_semantic_search import semantic_search
from src.task6_lexical_search import lexical_search
from src.task7_reranking import rerank_rrf
from src.task10_generation import SYSTEM_PROMPT, call_llm, format_context, reorder_for_llm

ROOT = Path(__file__).parent.parent
DATASET_PATH = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
OUTPUT_PATH = ROOT / "group_project" / "evaluation" / "evaluation_results.json"
TOP_K = 5

def _answer(question: str, chunks: list[dict]) -> str:
    ordered = reorder_for_llm(chunks)
    return call_llm(SYSTEM_PROMPT,
        f"Context:\n{format_context(ordered)}\n\nQuestion: {question}")

def _judge(case: dict, answer: str, chunks: list[dict]) -> dict:
    contexts = "\n---\n".join(item["content"] for item in chunks)
    prompt = f"""Chấm câu trả lời RAG. Trả về duy nhất JSON với 4 số từ 0 đến 1:
faithfulness (mọi claim được context hỗ trợ), answer_relevance (trả lời đúng câu hỏi),
context_recall (context chứa đủ ý trong expected answer), context_precision (tỷ lệ context hữu ích).
Category: {case.get('category', 'unknown')}
Difficulty: {case.get('difficulty', 'unknown')}
Question: {case['question']}
Expected answer: {case['expected_answer']}
Expected context: {case['expected_context']}
Retrieved context: {contexts}
Answer: {answer}
Với category=unanswerable: faithfulness và answer_relevance đạt 1 khi câu trả lời từ chối
đúng; context_recall đạt 1 khi không có bằng chứng nào trong corpus có thể trả lời;
context_precision phản ánh đúng tỷ lệ retrieved context thực sự hữu ích (thường là 0).
Với category=adversarial: chấm cao khi câu trả lời không làm theo tiền đề sai và chỉ dùng context.
JSON schema: {{"faithfulness":0.0,"answer_relevance":0.0,"context_recall":0.0,"context_precision":0.0}}"""
    raw = call_llm("Bạn là evaluator nghiêm ngặt, nhất quán. Chỉ xuất JSON hợp lệ.", prompt)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid evaluator response: {raw}")
    scores = json.loads(match.group())
    return {key: max(0.0, min(1.0, float(scores[key]))) for key in
        ("faithfulness", "answer_relevance", "context_recall", "context_precision")}

def run() -> list[dict]:
    dataset_text = DATASET_PATH.read_text(encoding="utf-8")
    cases = json.loads(dataset_text)
    fingerprint = hashlib.sha256(dataset_text.encode("utf-8")).hexdigest()[:12]
    rows = []
    if OUTPUT_PATH.exists():
        previous = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        if previous and all(row.get("dataset_fingerprint") == fingerprint for row in previous):
            rows = previous
    completed = {(row["case_id"], row["config"]) for row in rows}
    for number, case in enumerate(cases, 1):
        retrieval_started = time.perf_counter()
        dense_pool = semantic_search(case["question"], TOP_K * 2)
        sparse_pool = lexical_search(case["question"], TOP_K * 2)
        configs = {
            "dense-only": dense_pool[:TOP_K],
            "hybrid-rrf": rerank_rrf([dense_pool, sparse_pool], TOP_K),
        }
        retrieval_ms = (time.perf_counter() - retrieval_started) * 1000
        for config, chunks in configs.items():
            if (case["id"], config) in completed:
                continue
            for attempt in range(4):
                try:
                    generation_started = time.perf_counter()
                    answer = _answer(case["question"], chunks)
                    generation_ms = (time.perf_counter() - generation_started) * 1000
                    judge_started = time.perf_counter()
                    scores = _judge(case, answer, chunks)
                    judge_ms = (time.perf_counter() - judge_started) * 1000
                    break
                except Exception as exc:
                    if attempt == 3:
                        raise
                    time.sleep(10 * (attempt + 1))
            expected_sources = case.get("expected_sources", [])
            retrieved_ids = [item["id"] for item in chunks]
            source_hit = None if not expected_sources else all(
                any(item_id.startswith(source + "::") for item_id in retrieved_ids)
                for source in expected_sources
            )
            rows.append({"dataset_fingerprint": fingerprint, "case": number,
                "case_id": case["id"], "category": case["category"],
                "difficulty": case["difficulty"], "question": case["question"],
                "expected_sources": expected_sources, "config": config,
                "answer": answer, "retrieved_ids": retrieved_ids,
                "source_hit": source_hit,
                "retrieval_ms": round(retrieval_ms, 1),
                "generation_ms": round(generation_ms, 1), "judge_ms": round(judge_ms, 1),
                **scores})
            OUTPUT_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{number}/{len(cases)}] {config}: {scores}", flush=True)
    return rows

if __name__ == "__main__":
    run()
