"""
Đánh giá RAG trên golden dataset — A/B dense-only vs hybrid + RRF.

Hai config dùng cùng golden dataset, generator, evaluator, prompt và top_k; chỉ
khác retrieval strategy (use_reranking=False/True trong Task 9).

    # Chỉ đo retrieval (không cần API key): hit@k, MRR, context coverage
    python -m src.evaluate --retrieval-only

    # Đầy đủ: generation + 4 metric RAGAS (cần OPENAI_API_KEY)
    python -m src.evaluate

Kết quả: group_project/evaluation/results/{retrieval,ragas}_results.json
"""

import argparse
import asyncio
import json
import os
import re
import statistics
import time
import unicodedata
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

ROOT = Path(__file__).parent.parent
EVAL_DIR = ROOT / "group_project" / "evaluation"
GOLDEN_PATH = EVAL_DIR / "golden_dataset.json"
RESULTS_DIR = EVAL_DIR / "results"

TOP_K = 5
EVALUATOR_MODEL = os.getenv("EVALUATOR_MODEL", "gpt-4o-mini")
CONCURRENCY = 8
HIT_COVERAGE = 0.7

CONFIGS = {
    "A_dense": {"label": "Config A — dense-only", "use_reranking": False},
    "B_hybrid": {"label": "Config B — hybrid + RRF", "use_reranking": True},
}
METRICS = ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]


def load_golden() -> list[dict]:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", unicodedata.normalize("NFC", text).lower()))


def coverage(expected: str, retrieved: str) -> float:
    """Tỷ lệ âm tiết của expected_context có mặt trong đoạn retrieved."""
    expected_tokens = _tokens(expected)
    if not expected_tokens:
        return 0.0
    return len(expected_tokens & _tokens(retrieved)) / len(expected_tokens)


def retrieval_metrics(item: dict, results: list[dict]) -> dict:
    """hit@k và reciprocal rank theo chunk đầu tiên chứa expected_context."""
    first_hit = None
    for rank, result in enumerate(results, 1):
        same_source = result["id"].startswith(item["source"] + "::")
        if same_source and coverage(item["expected_context"], result["content"]) >= HIT_COVERAGE:
            first_hit = rank
            break
    joined = "\n".join(result["content"] for result in results)
    return {
        "hit": first_hit is not None,
        "reciprocal_rank": 1 / first_hit if first_hit else 0.0,
        "first_hit_rank": first_hit,
        "context_coverage": round(coverage(item["expected_context"], joined), 4),
        "retrieved_ids": [result["id"] for result in results],
    }


def summarize(rows: list[dict], keys: list[str]) -> dict:
    summary = {}
    for key in keys:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        summary[key] = round(statistics.mean(values), 4) if values else None
    return summary


def run_retrieval_only() -> dict:
    from .task5_semantic_search import semantic_search
    from .task6_lexical_search import lexical_search
    from .task9_retrieval_pipeline import retrieve

    golden = load_golden()
    semantic_search("warm-up", top_k=1)  # nạp embedding model trước khi đo latency
    strategies = {
        "dense": lambda query: semantic_search(query, top_k=TOP_K),
        "bm25": lambda query: lexical_search(query, top_k=TOP_K),
        "hybrid_rrf": lambda query: retrieve(query, top_k=TOP_K, use_reranking=True),
    }
    output = {"top_k": TOP_K, "hit_coverage_threshold": HIT_COVERAGE, "strategies": {}}
    for name, search in strategies.items():
        rows = []
        for item in golden:
            started = time.perf_counter()
            results = search(item["question"])
            latency = time.perf_counter() - started
            rows.append({"id": item["id"], "latency_s": round(latency, 4), **retrieval_metrics(item, results)})
        output["strategies"][name] = {
            "summary": summarize(rows, ["hit", "reciprocal_rank", "context_coverage", "latency_s"]),
            "rows": rows,
        }
        print(f"{name:11s} {output['strategies'][name]['summary']}")
    return output


def _ragas_components():
    from openai import AsyncOpenAI
    from ragas.embeddings.base import BaseRagasEmbedding
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    from .task4_chunking_indexing import embed_texts

    class PipelineEmbedding(BaseRagasEmbedding):
        """Dùng chung embed_texts() của pipeline (bge-m3) cho answer relevancy."""

        def embed_text(self, text, **kwargs):
            return embed_texts([text])[0]

        async def aembed_text(self, text, **kwargs):
            return await asyncio.to_thread(self.embed_text, text)

    llm = llm_factory(EVALUATOR_MODEL, client=AsyncOpenAI(), temperature=0)
    return {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=PipelineEmbedding()),
        "context_recall": ContextRecall(llm=llm),
        "context_precision": ContextPrecision(llm=llm),
    }


async def score_sample(metrics: dict, sample: dict, semaphore: asyncio.Semaphore) -> dict:
    contexts = sample["contexts"] or ["(không có context)"]
    calls = {
        "faithfulness": lambda: metrics["faithfulness"].ascore(
            user_input=sample["question"], response=sample["answer"], retrieved_contexts=contexts),
        "answer_relevancy": lambda: metrics["answer_relevancy"].ascore(
            user_input=sample["question"], response=sample["answer"]),
        "context_recall": lambda: metrics["context_recall"].ascore(
            user_input=sample["question"], retrieved_contexts=contexts, reference=sample["reference"]),
        "context_precision": lambda: metrics["context_precision"].ascore(
            user_input=sample["question"], reference=sample["reference"], retrieved_contexts=contexts),
    }
    scores = {}
    for name, call in calls.items():
        async with semaphore:
            try:
                scores[name] = float((await call()).value)
            except Exception as error:
                print(f"  ! {sample['id']} {name}: {error}")
                scores[name] = None
    return scores


def generate_samples(use_reranking: bool) -> list[dict]:
    from .task10_generation import generate_answer
    from .task9_retrieval_pipeline import retrieve

    samples = []
    for item in load_golden():
        started = time.perf_counter()
        result = generate_answer(item["question"], top_k=TOP_K, use_reranking=use_reranking)
        latency = time.perf_counter() - started
        # Retrieval metrics đo trên cùng danh sách chunk mà generator đã thấy.
        retrieved = result["sources"] or retrieve(item["question"], top_k=TOP_K, use_reranking=use_reranking)
        samples.append({
            "id": item["id"],
            "question": item["question"],
            "reference": item["expected_answer"],
            "answer": result["answer"],
            "retrieval_source": result["retrieval_source"],
            "contexts": [source["content"] for source in result["sources"]],
            "source_ids": [source["id"] for source in result["sources"]],
            "latency_s": round(latency, 3),
            **{key: value for key, value in retrieval_metrics(item, retrieved).items() if key != "retrieved_ids"},
        })
        print(f"  {item['id']} {latency:5.2f}s {result['answer'][:90]!r}")
    return samples


async def run_full() -> dict:
    from .task10_generation import LLM_MODEL, LLM_PROVIDER

    metrics = _ragas_components()
    semaphore = asyncio.Semaphore(CONCURRENCY)
    output = {
        "evaluated_at": datetime.now().isoformat(timespec="seconds"),
        "generator": f"{LLM_PROVIDER}/{LLM_MODEL}",
        "evaluator": f"openai/{EVALUATOR_MODEL}",
        "top_k": TOP_K,
        "configs": {},
    }
    for key, config in CONFIGS.items():
        print(f"\n{config['label']}: generating")
        samples = generate_samples(config["use_reranking"])
        print(f"{config['label']}: scoring with RAGAS")
        scores = await asyncio.gather(*(score_sample(metrics, sample, semaphore) for sample in samples))
        rows = [{**sample, **score} for sample, score in zip(samples, scores)]
        summary = summarize(rows, METRICS + ["hit", "reciprocal_rank", "latency_s"])
        metric_values = [summary[name] for name in METRICS if summary[name] is not None]
        summary["average"] = round(statistics.mean(metric_values), 4) if metric_values else None
        output["configs"][key] = {"label": config["label"], "summary": summary, "rows": rows}
        print(f"{config['label']}: {summary}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--retrieval-only", action="store_true", help="skip generation and RAGAS")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if args.retrieval_only:
        output, path = run_retrieval_only(), RESULTS_DIR / "retrieval_results.json"
    else:
        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit("OPENAI_API_KEY is not set in .env (needed for RAGAS evaluator)")
        output, path = asyncio.run(run_full()), RESULTS_DIR / "ragas_results.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
