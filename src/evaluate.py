"""Reproducible Gemini-judged A/B evaluation for dense versus hybrid retrieval."""
import json
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
Question: {case['question']}
Expected answer: {case['expected_answer']}
Expected context: {case['expected_context']}
Retrieved context: {contexts}
Answer: {answer}
JSON schema: {{"faithfulness":0.0,"answer_relevance":0.0,"context_recall":0.0,"context_precision":0.0}}"""
    raw = call_llm("Bạn là evaluator nghiêm ngặt, nhất quán. Chỉ xuất JSON hợp lệ.", prompt)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid evaluator response: {raw}")
    scores = json.loads(match.group())
    return {key: max(0.0, min(1.0, float(scores[key]))) for key in
        ("faithfulness", "answer_relevance", "context_recall", "context_precision")}

def run() -> list[dict]:
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    rows = []
    for number, case in enumerate(cases, 1):
        dense_pool = semantic_search(case["question"], TOP_K * 2)
        configs = {
            "dense-only": dense_pool[:TOP_K],
            "hybrid-rrf": rerank_rrf([dense_pool,
                lexical_search(case["question"], TOP_K * 2)], TOP_K),
        }
        for config, chunks in configs.items():
            for attempt in range(4):
                try:
                    answer = _answer(case["question"], chunks)
                    scores = _judge(case, answer, chunks)
                    break
                except Exception as exc:
                    if attempt == 3:
                        raise
                    time.sleep(10 * (attempt + 1))
            rows.append({"case": number, "question": case["question"],
                "expected_source": case.get("expected_source"), "config": config,
                "answer": answer, "retrieved_ids": [x["id"] for x in chunks], **scores})
            OUTPUT_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{number}/{len(cases)}] {config}: {scores}", flush=True)
    return rows

if __name__ == "__main__":
    run()
