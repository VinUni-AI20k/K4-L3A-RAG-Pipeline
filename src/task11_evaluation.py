"""
Task 11 — Evaluation 4 metric và so sánh A/B.

Hai cấu hình chỉ khác retrieval strategy, mọi thứ còn lại giữ nguyên
(golden dataset, generator, prompt, evaluator, top_k, fallback threshold):
    A  dense-only           : semantic_search, cắt top_k, không chạy RRF
    B  hybrid + RRF         : semantic_search + lexical_search gộp bằng RRF một lần
    C  hybrid + RRF + rerank: như B nhưng RRF lấy 2×top_k rồi cross-encoder
                              (Task 12, bonus) chấm lại và cắt top_k
    D  C + HyDE             : như C nhưng query tìm kiếm được nối thêm đoạn giả
                              định (Task 14, bonus); RRF gộp 3 danh sách

Metric (ragas 0.4.3, API collections):
    faithfulness       answer có bám vào retrieved contexts không
    answer_relevancy   answer có trả lời đúng câu hỏi không
    context_recall     retrieved contexts có phủ expected_context không
    context_precision  chunk liên quan có được xếp trên chunk nhiễu không

Evaluator LLM tách khỏi generator qua EVAL_MODEL / EVAL_EMBEDDING_MODEL trong
.env; mặc định dùng OpenAI vì instructor adapter của ragas ổn định nhất với
provider này.

Chạy:
    python -m src.task11_evaluation                 # cả A và B, 20 câu
    python -m src.task11_evaluation --config B      # chỉ một config
    python -m src.task11_evaluation --config C --skip-generate --skip-score
                                                    # in lại summary từ JSON đã có
    python -m src.task11_evaluation --limit 3       # smoke test
    python -m src.task11_evaluation --skip-generate # chấm lại từ answers đã lưu

Kết quả ghi vào group_project/evaluation/results/:
    config_A.json / config_B.json   per-question: answer, contexts, latency, scores
    summary.json                    điểm trung bình, delta, refusal count, latency
    summary.md                      bảng markdown để dán vào RESULT.md
"""

import argparse
import asyncio
import json
import math
import os
import statistics
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from .task10_generation import LLM_MODEL, LLM_PROVIDER, SAFE_REFUSAL, generate_from_chunks
from .task4_chunking_indexing import EMBEDDING_MODEL
from .task9_retrieval_pipeline import SCORE_THRESHOLD, retrieve_detailed


load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
RESULTS_DIR = ROOT / "group_project" / "evaluation" / "results"

TOP_K = 5
EVAL_MODEL = os.getenv("EVAL_MODEL", "gpt-4o-mini")
EVAL_EMBEDDING_MODEL = os.getenv("EVAL_EMBEDDING_MODEL", "text-embedding-3-small")
EVAL_CONCURRENCY = 4   # số câu chấm song song; giữ thấp để tránh rate limit

CONFIGS = {
    "A": {"label": "dense-only", "use_reranking": False, "use_cross_encoder": False, "use_hyde": False},
    "B": {"label": "hybrid + RRF", "use_reranking": True, "use_cross_encoder": False, "use_hyde": False},
    "C": {"label": "hybrid + RRF + rerank", "use_reranking": True, "use_cross_encoder": True, "use_hyde": False},
    "D": {"label": "C + HyDE", "use_reranking": True, "use_cross_encoder": True, "use_hyde": True},
}
METRICS = ("faithfulness", "answer_relevancy", "context_recall", "context_precision")


# --------------------------------------------------------------------------- #
# Bước 1: retrieval + generation cho từng config
# --------------------------------------------------------------------------- #

def load_golden(limit: int | None = None) -> list[dict]:
    dataset = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    return dataset[:limit] if limit else dataset


def run_config(config_key: str, golden: list[dict]) -> list[dict]:
    """Retrieve + generate cho mỗi câu; trả về list record chưa có score."""
    config = CONFIGS[config_key]
    records = []
    for index, case in enumerate(golden, 1):
        question = case["question"]

        started = time.perf_counter()
        detail = retrieve_detailed(
            question,
            top_k=TOP_K,
            use_reranking=config["use_reranking"],
            use_cross_encoder=config["use_cross_encoder"],
            use_hyde=config["use_hyde"],
        )
        retrieval_ms = (time.perf_counter() - started) * 1000
        chunks = detail["results"][:TOP_K]

        started = time.perf_counter()
        generation = generate_from_chunks(question, chunks)
        generation_ms = (time.perf_counter() - started) * 1000

        is_refusal = generation["answer"] == SAFE_REFUSAL
        records.append({
            "id": case.get("id", f"q{index:02d}"),
            "category": case.get("category"),
            "question": question,
            "expected_answer": case["expected_answer"],
            "expected_context": case["expected_context"],
            "expected_source": case.get("source"),
            "answer": generation["answer"],
            "is_refusal": is_refusal,
            "retrieval_source": detail["retrieval_source"],
            "best_dense_score": round(detail["best_dense_score"], 4),
            "fallback_tried": detail["fallback_tried"],
            "reranked": detail.get("reranked", False),
            "reranker_error": detail.get("reranker_error"),
            "hyde_query": detail.get("hyde_query"),
            "contexts": [
                {
                    "id": chunk["id"],
                    "source": chunk["metadata"]["source"],
                    "score": round(float(chunk["score"]), 4),
                    "retrieval_method": chunk["retrieval_method"],
                    "content": chunk["content"],
                }
                for chunk in chunks
            ],
            "latency_ms": {
                "retrieval": round(retrieval_ms, 1),
                "generation": round(generation_ms, 1),
            },
            "scores": {},
        })
        flag = "REFUSAL" if is_refusal else "ok"
        print(
            f"[{config_key}] {index:>2}/{len(golden)} {flag:<7} "
            f"dense={detail['best_dense_score']:.3f} src={detail['retrieval_source']:<9} "
            f"{question[:60]}"
        )
    return records


# --------------------------------------------------------------------------- #
# Bước 2: chấm điểm bằng ragas
# --------------------------------------------------------------------------- #

def build_metrics() -> dict:
    from openai import AsyncOpenAI
    from ragas.embeddings import OpenAIEmbeddings
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is required for the ragas evaluator")
    client = AsyncOpenAI()
    llm = llm_factory(EVAL_MODEL, provider="openai", client=client)
    embeddings = OpenAIEmbeddings(client=client, model=EVAL_EMBEDDING_MODEL)
    return {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=embeddings),
        "context_recall": ContextRecall(llm=llm),
        "context_precision": ContextPrecision(llm=llm),
    }


async def _score_one(metrics: dict, record: dict, semaphore: asyncio.Semaphore) -> None:
    contexts = [item["content"] for item in record["contexts"]] or ["(no context retrieved)"]
    question, answer, reference = record["question"], record["answer"], record["expected_context"]
    calls = {
        "faithfulness": lambda: metrics["faithfulness"].ascore(
            user_input=question, response=answer, retrieved_contexts=contexts
        ),
        "answer_relevancy": lambda: metrics["answer_relevancy"].ascore(
            user_input=question, response=answer
        ),
        "context_recall": lambda: metrics["context_recall"].ascore(
            user_input=question, retrieved_contexts=contexts, reference=reference
        ),
        "context_precision": lambda: metrics["context_precision"].ascore(
            user_input=question, reference=reference, retrieved_contexts=contexts
        ),
    }
    async with semaphore:
        for name, call in calls.items():
            try:
                result = await call()
                value = float(result.value)
                record["scores"][name] = None if math.isnan(value) else round(value, 4)
            except Exception as error:  # noqa: BLE001 - một metric lỗi không được làm hỏng cả run
                record["scores"][name] = None
                record.setdefault("errors", {})[name] = f"{type(error).__name__}: {error}"


async def score_records(records: list[dict]) -> None:
    metrics = build_metrics()
    semaphore = asyncio.Semaphore(EVAL_CONCURRENCY)
    await asyncio.gather(*(_score_one(metrics, record, semaphore) for record in records))


# --------------------------------------------------------------------------- #
# Bước 3: tổng hợp
# --------------------------------------------------------------------------- #

def _mean(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return round(statistics.fmean(clean), 4) if clean else None


def summarize(records: list[dict]) -> dict:
    summary = {
        "n": len(records),
        "refusals": sum(record["is_refusal"] for record in records),
        "pageindex_fallbacks": sum(record["retrieval_source"] == "pageindex" for record in records),
        "metrics": {name: _mean([r["scores"].get(name) for r in records]) for name in METRICS},
        "latency_ms": {
            stage: _mean([r["latency_ms"][stage] for r in records])
            for stage in ("retrieval", "generation")
        },
    }
    metric_values = [v for v in summary["metrics"].values() if v is not None]
    summary["average"] = round(statistics.fmean(metric_values), 4) if metric_values else None
    return summary


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def _delta(a: float | None, b: float | None) -> str:
    return "n/a" if a is None or b is None else f"{b - a:+.4f}"


def write_summary(all_records: dict[str, list[dict]]) -> None:
    summaries = {key: summarize(records) for key, records in all_records.items()}
    run_info = {
        "evaluation_date": date.today().isoformat(),
        "framework": "ragas 0.4.3",
        "evaluator_model": f"{EVAL_MODEL} (+ {EVAL_EMBEDDING_MODEL} for answer_relevancy)",
        "generator_model": f"{LLM_PROVIDER}/{LLM_MODEL}",
        "embedding_model": EMBEDDING_MODEL,
        "corpus_commit": _git_commit(),
        "golden_dataset_size": len(next(iter(all_records.values()))),
        "top_k": TOP_K,
        "score_threshold": SCORE_THRESHOLD,
    }
    (RESULTS_DIR / "summary.json").write_text(
        json.dumps({"run_info": run_info, "configs": summaries}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    keys = list(summaries)
    base = summaries.get("A") or summaries[keys[0]]
    others = [key for key in keys if summaries[key] is not base]
    lines = ["# Evaluation summary", "", "## Run information", ""]
    lines += [f"- {key}: `{value}`" for key, value in run_info.items()]
    lines += ["", "## Overall scores", ""]
    header = "| Metric | " + " | ".join(f"Config {key}" for key in keys)
    header += "".join(f" | Delta {key}−A" for key in others) + " |"
    lines += [header, "| --- |" + " ---: |" * (len(keys) + len(others))]
    for name in METRICS:
        row = f"| {name} | " + " | ".join(_fmt(summaries[key]["metrics"][name]) for key in keys)
        row += "".join(f" | {_delta(base['metrics'][name], summaries[key]['metrics'][name])}" for key in others)
        lines.append(row + " |")
    row = "| **Average** | " + " | ".join(_fmt(summaries[key]["average"]) for key in keys)
    row += "".join(f" | {_delta(base['average'], summaries[key]['average'])}" for key in others)
    lines.append(row + " |")

    lines += ["", "## Latency and refusals", ""]
    lines += ["| Config | Refusals | PageIndex fallback | Retrieval ms | Generation ms |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for key, summary in summaries.items():
        lines.append(
            f"| {key} ({CONFIGS[key]['label']}) | {summary['refusals']}/{summary['n']} | "
            f"{summary['pageindex_fallbacks']} | {_fmt(summary['latency_ms']['retrieval'])} | "
            f"{_fmt(summary['latency_ms']['generation'])} |"
        )

    lines += ["", "## Per-question scores", ""]
    header = "| # | Config | Faithfulness | Relevance | Recall | Precision | Refusal | Question |"
    lines += [header, "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |"]
    for key, records in all_records.items():
        for record in records:
            s = record["scores"]
            lines.append(
                f"| {record['id']} | {key} | {_fmt(s.get('faithfulness'))} | "
                f"{_fmt(s.get('answer_relevancy'))} | {_fmt(s.get('context_recall'))} | "
                f"{_fmt(s.get('context_precision'))} | {'yes' if record['is_refusal'] else ''} | "
                f"{record['question']} |"
            )
    (RESULTS_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[: 8 + len(METRICS) + 8]))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", choices=list(CONFIGS), action="append",
                        help="chỉ chạy config này (mặc định: tất cả)")
    parser.add_argument("--limit", type=int, default=None, help="số câu golden để smoke test")
    parser.add_argument("--skip-generate", action="store_true",
                        help="dùng lại config_X.json đã có, chỉ chấm lại điểm")
    parser.add_argument("--skip-score", action="store_true",
                        help="chỉ retrieval + generation, không gọi ragas")
    args = parser.parse_args(argv)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    golden = load_golden(args.limit)
    keys = args.config or list(CONFIGS)

    all_records: dict[str, list[dict]] = {}
    for key in keys:
        path = RESULTS_DIR / f"config_{key}.json"
        if args.skip_generate and path.exists():
            records = json.loads(path.read_text(encoding="utf-8"))
            if args.limit:
                records = records[: args.limit]
            print(f"[{key}] loaded {len(records)} records from {path.name}")
        else:
            print(f"\n=== Config {key}: {CONFIGS[key]['label']} ===")
            records = run_config(key, golden)
            path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

        if not args.skip_score:
            print(f"[{key}] scoring {len(records)} records with {EVAL_MODEL} ...")
            asyncio.run(score_records(records))
            path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
            errors = sum(len(r.get("errors", {})) for r in records)
            if errors:
                print(f"[{key}] {errors} metric call(s) failed; see 'errors' in {path.name}")
        all_records[key] = records

    if not args.skip_score or args.skip_generate:
        # skip-generate + skip-score: chỉ dựng lại summary từ JSON đã chấm.
        write_summary(all_records)
        print(f"\nWrote {RESULTS_DIR.relative_to(ROOT)}/summary.json and summary.md")


if __name__ == "__main__":
    main(sys.argv[1:])
