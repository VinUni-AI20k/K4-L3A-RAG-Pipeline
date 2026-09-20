"""Reproducible A/B evaluation: dense-only vs dense + BM25 + RRF."""

import json
import re
import time
from pathlib import Path

from src.task10_generation import SYSTEM_PROMPT, call_llm, format_context, reorder_for_llm
from src.task5_semantic_search import semantic_search
from src.task6_lexical_search import lexical_search
from src.task7_reranking import rerank_rrf


HERE = Path(__file__).parent
DATASET = HERE / "golden_dataset.json"
DETAILS = HERE / "evaluation_details.json"
TOP_K = 5
STOPWORDS = {
    "và", "là", "có", "được", "của", "cho", "trong", "với", "khi", "từ",
    "đến", "theo", "một", "các", "sinh", "viên", "học", "thì", "phải", "không",
    "vào", "về", "những", "này", "bao", "nhiêu", "như", "thế", "nào",
}


def tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"\w+", text.casefold())
        if len(token) > 1 and token not in STOPWORDS
    }


def f1(reference: set[str], candidate: set[str]) -> float:
    if not reference or not candidate:
        return 0.0
    overlap = len(reference & candidate)
    precision = overlap / len(candidate)
    recall = overlap / len(reference)
    return 2 * precision * recall / (precision + recall) if overlap else 0.0


def metric_scores(case: dict, answer: str, contexts: list[dict]) -> dict[str, float]:
    expected_answer = tokens(case["expected_answer"])
    expected_context = tokens(case["expected_context"])
    answer_tokens = tokens(re.sub(r"\[S\d+\]", "", answer))
    context_sets = [tokens(item["content"]) for item in contexts]
    all_context = set().union(*context_sets) if context_sets else set()
    relevant = [
        chunk for chunk in context_sets
        if expected_context and len(chunk & expected_context) / len(expected_context) >= 0.25
    ]
    return {
        "faithfulness": len(answer_tokens & all_context) / len(answer_tokens) if answer_tokens else 0.0,
        "answer_relevance": f1(expected_answer, answer_tokens),
        "context_recall": len(expected_context & all_context) / len(expected_context) if expected_context else 0.0,
        "context_precision": len(relevant) / len(context_sets) if context_sets else 0.0,
    }


def retrieve(question: str, hybrid: bool) -> list[dict]:
    dense = semantic_search(question, TOP_K * 2)
    if not hybrid:
        return dense[:TOP_K]
    sparse = lexical_search(question, TOP_K * 2)
    return rerank_rrf([dense, sparse], TOP_K)


def generate(question: str, contexts: list[dict]) -> str:
    ordered = reorder_for_llm(contexts)
    prompt = f"Context:\n{format_context(ordered)}\n\nQuestion: {question}"
    for attempt in range(3):
        try:
            return call_llm(SYSTEM_PROMPT, prompt)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def main() -> None:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    saved = json.loads(DETAILS.read_text(encoding="utf-8")) if DETAILS.exists() else []
    completed = {(row["config"], row["question"]) for row in saved}

    for config, hybrid in (("A", False), ("B", True)):
        for index, case in enumerate(cases, 1):
            key = (config, case["question"])
            if key in completed:
                continue
            started = time.perf_counter()
            contexts = retrieve(case["question"], hybrid)
            answer = generate(case["question"], contexts)
            row = {
                "case": index,
                "config": config,
                "question": case["question"],
                "answer": answer,
                "context_ids": [item["id"] for item in contexts],
                "latency_seconds": round(time.perf_counter() - started, 3),
                **{key: round(value, 4) for key, value in metric_scores(case, answer, contexts).items()},
            }
            saved.append(row)
            DETAILS.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{config} {index:02d}/{len(cases)} done")

    for config in ("A", "B"):
        rows = [row for row in saved if row["config"] == config]
        summary = {
            metric: round(sum(row[metric] for row in rows) / len(rows), 4)
            for metric in ("faithfulness", "answer_relevance", "context_recall", "context_precision")
        }
        summary["latency_seconds"] = round(sum(row["latency_seconds"] for row in rows) / len(rows), 3)
        print(config, summary)


if __name__ == "__main__":
    main()
