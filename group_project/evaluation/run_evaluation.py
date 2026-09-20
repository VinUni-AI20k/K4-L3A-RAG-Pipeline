"""Run the same IELTS questions through dense and hybrid retrieval, then score them.

Usage:
    python -m group_project.evaluation.run_evaluation --generate
    python -m group_project.evaluation.run_evaluation --score
"""

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.task10_generation import (
    LLM_MODEL,
    LLM_PROVIDER,
    SAFE_REFUSAL,
    SYSTEM_PROMPT,
    call_llm,
    format_context,
    reorder_for_llm,
)
from src.task4_chunking_indexing import EMBEDDING_MODEL, STANDARDIZED_DIR
from src.task5_semantic_search import semantic_search
from src.task9_retrieval_pipeline import SCORE_THRESHOLD, retrieve


ROOT = Path(__file__).resolve().parents[2]
GOLDEN = Path(__file__).with_name("golden_dataset.json")
OUTPUT = Path(__file__).with_name("run_results.json")
TOP_K = 5
METRICS = ("faithfulness", "answer_relevancy", "context_recall", "context_precision")


def _write(payload: dict) -> None:
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)


def _golden() -> tuple[list[dict], str]:
    raw = GOLDEN.read_bytes()
    cases = json.loads(raw)
    if len(cases) < 15:
        raise ValueError("Golden dataset needs at least 15 cases")
    for case in cases:
        for key in ("question", "expected_answer", "expected_context", "source"):
            if not case.get(key):
                raise ValueError(f"Missing {key} in golden case")
        if not (STANDARDIZED_DIR / case["source"]).is_file():
            raise ValueError(f"Golden source missing: {case['source']}")
    return cases, hashlib.sha256(raw).hexdigest()


def _answer(query: str, chunks: list[dict]) -> str:
    if not chunks:
        return SAFE_REFUSAL
    context = format_context(reorder_for_llm(chunks))
    answer = call_llm(SYSTEM_PROMPT, f"Context:\n{context}\n\nQuestion: {query}")
    cited = re.findall(r"\[([^\[\]\n]+)\]", answer)
    ids = {chunk["id"] for chunk in chunks}
    if not cited or any(item_id not in ids for item_id in cited):
        return SAFE_REFUSAL
    return answer.strip()


def generate() -> None:
    cases, digest = _golden()
    if LLM_PROVIDER.lower() != "openai":
        raise ValueError("This evaluation script currently uses the configured OpenAI model as the Ragas judge")
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "golden_sha256": digest,
        "generator_model": LLM_MODEL,
        "evaluator_model": LLM_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "top_k": TOP_K,
        "fallback_threshold": SCORE_THRESHOLD,
        "configurations": {
            "A": "dense-only",
            "B": "dense + BM25 fused once with RRF; fallback disabled for this comparison",
        },
        "runs": {"A": [], "B": []},
        "scores": {},
    }
    if OUTPUT.exists():
        existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if existing["golden_sha256"] != digest or existing["generator_model"] != LLM_MODEL:
            raise ValueError("Existing run uses a different golden dataset or generator model")
        payload = existing

    for config in ("A", "B"):
        for index, case in enumerate(cases[len(payload["runs"][config]):], len(payload["runs"][config]) + 1):
            query = case["question"]
            started = time.monotonic()
            if config == "A":
                chunks = semantic_search(query, top_k=TOP_K)
            else:
                chunks = retrieve(query, top_k=TOP_K, score_threshold=0.0, use_reranking=True)
            answer = _answer(query, chunks)
            row = {
                "question": query,
                "reference": case["expected_answer"],
                "expected_context": case["expected_context"],
                "expected_source": case["source"],
                "answer": answer,
                "sources": chunks,
                "latency_seconds": round(time.monotonic() - started, 3),
            }
            payload["runs"][config].append(row)
            _write(payload)
            print(f"{config} {index}/{len(cases)}: {len(chunks)} chunks, {row['latency_seconds']:.1f}s", flush=True)


def score() -> None:
    from datasets import Dataset
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
    from ragas.run_config import RunConfig

    cases, digest = _golden()
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    if payload["golden_sha256"] != digest:
        raise ValueError("Golden dataset changed since the answers were generated")
    judge = ChatOpenAI(model=payload["evaluator_model"], temperature=0, timeout=45, max_retries=1)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", timeout=45, max_retries=1)

    for config in ("A", "B"):
        rows = payload["runs"][config]
        if len(rows) != len(cases):
            raise ValueError(f"Configuration {config} has only {len(rows)} of {len(cases)} answers")
        if config in payload["scores"]:
            continue
        dataset = Dataset.from_list([
            {
                "user_input": row["question"],
                "response": row["answer"],
                "retrieved_contexts": [source["content"] for source in row["sources"]],
                "reference": row["reference"],
            }
            for row in rows
        ])
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
            llm=judge,
            embeddings=embeddings,
            run_config=RunConfig(timeout=60, max_retries=2, max_workers=4),
            raise_exceptions=True,
            show_progress=True,
        )
        scored_rows = result.to_pandas()[list(METRICS)].to_dict("records")
        payload["scores"][config] = scored_rows
        _write(payload)
        averages = {
            name: round(sum(row[name] for row in scored_rows) / len(scored_rows), 4)
            for name in METRICS
        }
        print(config, averages, flush=True)


if __name__ == "__main__":
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--score", action="store_true")
    arguments = parser.parse_args()
    if not arguments.generate and not arguments.score:
        parser.error("Choose --generate or --score")
    if arguments.generate:
        generate()
    if arguments.score:
        score()
