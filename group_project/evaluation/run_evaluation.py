"""Run the 15+ Q&A golden dataset through the chatbot and score it with ragas.

Compares Config A (dense-only retrieval) against Config B (hybrid + RRF),
using the same golden dataset, generator, judge model and top_k for both -
only the retrieval strategy changes, per docs/STEP_BY_STEP.md item 9.

Usage:
    python group_project/evaluation/run_evaluation.py

Requires (in .env):
    - Whatever LLM_PROVIDER/*_API_KEY the chatbot itself uses, to generate answers.
    - OPENAI_API_KEY for the ragas judge (faithfulness/relevancy/recall/precision
      all need an LLM-as-judge + embeddings; this script uses OpenAI for that
      role regardless of LLM_PROVIDER, since langchain-openai is a project
      dependency and the others are not).
"""

import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from chatbot import engine  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
GOLDEN_PATH = EVAL_DIR / "golden_dataset.json"
RAW_RESULTS_PATH = EVAL_DIR / "eval_raw_results.json"
RESULT_MD_PATH = EVAL_DIR / "RESULT.md"

TOP_K = 5
METRIC_NAMES = ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]


def run_config(golden: list[dict], use_hybrid: bool) -> list[dict]:
    rows = []
    label = "hybrid+RRF" if use_hybrid else "dense-only"
    for item in golden:
        print(f"  [{label}] {item['id']}: {item['question'][:60]}...")
        result = engine.generate_with_citation(item["question"], top_k=TOP_K, use_hybrid=use_hybrid)
        rows.append(
            {
                "id": item["id"],
                "question": item["question"],
                "answer": result["answer"],
                "contexts": [s["content"] for s in result["sources"]] or [""],
                "ground_truth": item["expected_answer"],
                "reference_context": item["expected_context"],
                "retrieval_method": result["retrieval_method"],
            }
        )
    return rows


def _build_judge():
    """ragas 0.4 uses instructor/litellm-based LLMs, not langchain wrappers.

    Reuses whatever LLM_PROVIDER/API key the chatbot itself is already
    configured with (openai/gemini via litellm+instructor), instead of
    hard-requiring a separate OpenAI key.
    """
    import os

    import instructor
    from litellm import acompletion
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    provider = engine.config.LLM_PROVIDER
    model_name = engine.config.LLM_MODEL or engine.config.DEFAULT_MODELS.get(provider, "")
    key_env = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }.get(provider)
    litellm_prefix = {"openai": "openai", "gemini": "gemini", "anthropic": "anthropic"}.get(provider)
    if not key_env or not litellm_prefix:
        raise RuntimeError(f"Unsupported LLM_PROVIDER for ragas judge: {provider!r}")
    if not os.getenv(key_env):
        raise RuntimeError(f"{key_env} is required in .env to run the ragas judge.")

    instructor_client = instructor.from_litellm(acompletion)
    judge_llm = llm_factory(
        f"{litellm_prefix}/{model_name}", provider=provider, client=instructor_client, adapter="litellm"
    )

    if provider == "gemini":
        from google import genai
        from ragas.embeddings import GoogleEmbeddings

        genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        judge_embeddings = GoogleEmbeddings(client=genai_client, model="text-embedding-004")
    elif provider == "openai":
        from openai import AsyncOpenAI
        from ragas.embeddings import OpenAIEmbeddings as RagasOpenAIEmbeddings

        judge_embeddings = RagasOpenAIEmbeddings(client=AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")))
    else:
        raise RuntimeError(
            "answer_relevancy needs an embeddings-capable judge provider "
            "(openai or gemini); anthropic alone is not supported by this script."
        )

    return {
        "faithfulness": Faithfulness(llm=judge_llm),
        "answer_relevancy": AnswerRelevancy(llm=judge_llm, embeddings=judge_embeddings),
        "context_recall": ContextRecall(llm=judge_llm),
        "context_precision": ContextPrecision(llm=judge_llm),
    }


async def _score_row_async(metrics: dict, row: dict) -> None:
    faithfulness_result = await metrics["faithfulness"].ascore(
        user_input=row["question"],
        response=row["answer"],
        retrieved_contexts=row["contexts"],
    )
    relevancy_result = await metrics["answer_relevancy"].ascore(
        user_input=row["question"], response=row["answer"]
    )
    recall_result = await metrics["context_recall"].ascore(
        user_input=row["question"],
        retrieved_contexts=row["contexts"],
        reference=row["ground_truth"],
    )
    precision_result = await metrics["context_precision"].ascore(
        user_input=row["question"],
        reference=row["ground_truth"],
        retrieved_contexts=row["contexts"],
    )
    row["faithfulness"] = faithfulness_result.value
    row["answer_relevancy"] = relevancy_result.value
    row["context_recall"] = recall_result.value
    row["context_precision"] = precision_result.value


async def _score_rows_async(rows: list[dict]) -> list[dict]:
    metrics = _build_judge()
    for row in rows:
        await _score_row_async(metrics, row)
    return rows


def compute_ragas(rows: list[dict]) -> list[dict]:
    import asyncio

    return asyncio.run(_score_rows_async(rows))


def averages(rows: list[dict]) -> dict:
    return {name: round(mean(r[name] for r in rows if r.get(name) is not None), 3) for name in METRIC_NAMES}


def render_result_md(rows_a: list[dict], rows_b: list[dict], golden: list[dict]) -> None:
    avg_a = averages(rows_a)
    avg_b = averages(rows_b)
    delta = {name: round(avg_b[name] - avg_a[name], 3) for name in METRIC_NAMES}
    overall_a = round(mean(avg_a.values()), 3)
    overall_b = round(mean(avg_b.values()), 3)

    combined = [{**row, "config": "B-hybrid"} for row in rows_b] + [
        {**row, "config": "A-dense"} for row in rows_a
    ]
    combined.sort(key=lambda r: mean(r[name] for name in METRIC_NAMES if r.get(name) is not None))
    worst = combined[:3]

    def fmt(value):
        return f"{value:.3f}" if isinstance(value, float) else str(value)

    worst_rows = "\n".join(
        f"|   {i} | {r['question'][:60].replace('|', '/')} | {r['config']} | "
        f"{fmt(r['faithfulness'])} | {fmt(r['answer_relevancy'])} | "
        f"{fmt(r['context_recall'])} | {fmt(r['context_precision'])} | retrieval/generation | TODO: phân tích thủ công |"
        for i, r in enumerate(worst, 1)
    )

    better = "Config B (hybrid + RRF)" if overall_b >= overall_a else "Config A (dense-only)"

    content = f"""# RAG evaluation results

## Run information

| Field                              | Value |
| ----------------------------------- | ----- |
| Evaluation date                    | {__import__('datetime').date.today().isoformat()} |
| Framework and version              | ragas |
| Evaluator model                    | gpt-4o-mini (OpenAI, LLM-as-judge) |
| Generator model                    | {engine.config.LLM_PROVIDER} / {engine.config.LLM_MODEL or engine.config.DEFAULT_MODELS.get(engine.config.LLM_PROVIDER, '')} |
| Embedding model                    | {engine.config.EMBEDDING_MODEL} (fastembed/ONNX) |
| Corpus version/commit              | data/standardized/legal (luat-nha-o, luat-kinh-doanh-bds, mau-so-1a) |
| Golden dataset size                | {len(golden)} |
| `top_k`                            | {TOP_K} |
| Fallback threshold and calibration | Không dùng fallback PageIndex trong bản demo này; chỉ so sánh dense-only và hybrid+RRF |

## Configurations

- **Config A — dense-only:** `chatbot.engine.retrieve(query, top_k={TOP_K}, use_hybrid=False)` - chỉ dùng cosine similarity trên embedding.
- **Config B — hybrid + RRF:** `chatbot.engine.retrieve(query, top_k={TOP_K}, use_hybrid=True)` - dense + BM25 gộp bằng RRF (k=60).

Hai cấu hình dùng chung golden dataset, generator, evaluator, prompt và `top_k`; chỉ khác retrieval strategy.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      | {avg_a['faithfulness']} | {avg_b['faithfulness']} | {delta['faithfulness']} |
| Answer relevance  | {avg_a['answer_relevancy']} | {avg_b['answer_relevancy']} | {delta['answer_relevancy']} |
| Context recall    | {avg_a['context_recall']} | {avg_b['context_recall']} | {delta['context_recall']} |
| Context precision | {avg_a['context_precision']} | {avg_b['context_precision']} | {delta['context_precision']} |
| **Average**       | {overall_a} | {overall_b} | {round(overall_b - overall_a, 3)} |

## A/B comparison

- Cấu hình tốt hơn: {better}
- Evidence: Xem bảng Overall scores ở trên và chi tiết từng câu hỏi trong `eval_raw_results.json`.
- Trade-off về latency/cost: Hybrid+RRF gọi thêm BM25 (rẻ, tại chỗ) nên chi phí tăng không đáng kể so với dense-only; độ trễ tăng nhẹ do phải tính thêm điểm BM25 và gộp RRF trước khi gọi LLM.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage             | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------------------- | ---------- |
{worst_rows}

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Xem lại 3 câu điểm thấp nhất ở trên, kiểm tra chunk trả về có đúng điều luật không | Bảng Worst performers | Tăng context precision/recall | Chạy lại run_evaluation.py sau khi chỉnh chunking |
|        2 | Cân nhắc thêm PageIndex hoặc mở rộng top_k cho câu hỏi có ngữ cảnh dàn trải nhiều điều luật | So sánh recall giữa 2 config | Tăng context recall | Đo lại recall trên các câu hỏi đa điều luật |
|        3 | Bổ sung thêm literal keyword (số điều, tên nghị định) vào câu hỏi khó để tận dụng BM25 | So sánh answer relevance dense vs hybrid | Tăng answer relevance | So sánh điểm relevance trước/sau |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | ------------------: | ---------- |
| TODO       | TODO     |         TODO |               TODO | TODO       |
"""
    RESULT_MD_PATH.write_text(content, encoding="utf-8")


def main() -> None:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(golden)} golden Q&A cases")

    print("Running Config A (dense-only)...")
    rows_a = run_config(golden, use_hybrid=False)
    print("Running Config B (hybrid + RRF)...")
    rows_b = run_config(golden, use_hybrid=True)

    print("Scoring Config A with ragas...")
    rows_a = compute_ragas(rows_a)
    print("Scoring Config B with ragas...")
    rows_b = compute_ragas(rows_b)

    RAW_RESULTS_PATH.write_text(
        json.dumps({"config_a_dense": rows_a, "config_b_hybrid": rows_b}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    render_result_md(rows_a, rows_b, golden)
    print(f"Done. Wrote {RAW_RESULTS_PATH.name} and {RESULT_MD_PATH.name}")


if __name__ == "__main__":
    main()
