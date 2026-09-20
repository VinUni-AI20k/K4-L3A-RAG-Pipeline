"""Reproducible 15-case evaluation for dense-only versus hybrid + RRF.

The evaluator is deliberately deterministic and local: lexical token overlap is
used for the four reported signals, while the same OpenAI generator/prompt is
used for both retrieval configurations. This avoids mixing evaluator-model
judgment with retrieval changes and makes the report rerunnable without extra
API calls beyond answer generation.
"""

import json
import re
import statistics
import time
from pathlib import Path

from .task5_semantic_search import semantic_search
from .task7_reranking import rerank_rrf
from .task10_generation import SYSTEM_PROMPT, call_llm, format_context, reorder_for_llm


ROOT = Path(__file__).parent.parent
EVALUATION_DIR = ROOT / "group_project" / "evaluation"
DATASET_PATH = EVALUATION_DIR / "golden_dataset.json"
RUN_PATH = EVALUATION_DIR / "evaluation_runs.json"
TOP_K = 5
STOPWORDS = set("là là gì của một và cho trong với theo nào những được có từ các một".split())


def tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
        if len(token) > 1 and token not in STOPWORDS
    }


def f1(predicted: set[str], expected: set[str]) -> float:
    if not predicted or not expected:
        return 0.0
    precision = len(predicted & expected) / len(predicted)
    recall = len(predicted & expected) / len(expected)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def score_case(case: dict, answer: str, chunks: list[dict]) -> dict[str, float]:
    context = "\n".join(chunk["content"] for chunk in chunks)
    answer_tokens = tokens(answer)
    context_tokens = tokens(context)
    expected_answer = tokens(case["expected_answer"])
    expected_context = tokens(case["expected_context"])
    faithfulness = len(answer_tokens & context_tokens) / len(answer_tokens) if answer_tokens else 0.0
    answer_relevance = f1(answer_tokens, expected_answer)
    context_recall = len(expected_context & context_tokens) / len(expected_context) if expected_context else 0.0
    relevant = sum(
        1 for chunk in chunks
        if len(tokens(case["expected_context"]) & tokens(chunk["content"]))
        / max(1, len(expected_context)) >= 0.35
    )
    context_precision = relevant / len(chunks) if chunks else 0.0
    return {
        "faithfulness": round(faithfulness, 4),
        "answer_relevance": round(answer_relevance, 4),
        "context_recall": round(context_recall, 4),
        "context_precision": round(context_precision, 4),
    }


def answer_case(case: dict, chunks: list[dict]) -> str:
    context = format_context(reorder_for_llm(chunks))
    return call_llm(
        SYSTEM_PROMPT,
        f"Context:\n{context}\n\nQuestion: {case['question']}",
    )


def run() -> dict:
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    if len(cases) < 15:
        raise ValueError("Golden dataset phải có ít nhất 15 câu")
    all_rows = []
    for index, case in enumerate(cases, 1):
        dense = semantic_search(case["question"], top_k=TOP_K)
        # Include BM25 through the public pipeline without triggering PageIndex.
        from .task6_lexical_search import lexical_search
        hybrid = rerank_rrf(
            [dense, lexical_search(case["question"], top_k=TOP_K * 2)], top_k=TOP_K
        )
        for config, chunks in (("dense-only", dense), ("hybrid + RRF", hybrid)):
            answer = answer_case(case, chunks)
            all_rows.append({
                "id": case["id"], "question": case["question"], "config": config,
                "answer": answer, "chunk_ids": [chunk["id"] for chunk in chunks],
                "metrics": score_case(case, answer, chunks),
            })
            print(f"{index:02d}/15 {config}: {case['id']}", flush=True)
            time.sleep(0.1)

    summary = {}
    for config in ("dense-only", "hybrid + RRF"):
        rows = [row for row in all_rows if row["config"] == config]
        metrics = {
            name: round(statistics.mean(row["metrics"][name] for row in rows), 4)
            for name in ("faithfulness", "answer_relevance", "context_recall", "context_precision")
        }
        metrics["average"] = round(statistics.mean(metrics.values()), 4)
        summary[config] = metrics
    payload = {"top_k": TOP_K, "summary": summary, "rows": all_rows}
    RUN_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run()
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
