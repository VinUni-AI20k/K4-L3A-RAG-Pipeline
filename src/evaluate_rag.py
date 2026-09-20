"""
Evaluation — A/B giữa dense-only và hybrid + RRF.

Hai config dùng chung golden dataset, generator, evaluator, prompt và top_k;
biến duy nhất thay đổi là retrieval strategy (`use_reranking`).

Chạy:
    python -m src.evaluate_rag
Kết quả thô được ghi ra group_project/evaluation/results_raw.json.
"""

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from .task4_chunking_indexing import embed_texts
from .task9_retrieval_pipeline import retrieve
from .task10_generation import (
    REFUSAL,
    SYSTEM_PROMPT,
    call_llm,
    format_context,
    reorder_for_llm,
)


load_dotenv()

EVALUATION_DIR = Path(__file__).parent.parent / "group_project" / "evaluation"
GOLDEN_PATH = EVALUATION_DIR / "golden_dataset.json"
RAW_RESULTS_PATH = EVALUATION_DIR / "results_raw.json"

TOP_K = 5
CONFIGS = {
    "A_dense_only": {"use_reranking": False},
    "B_hybrid_rrf": {"use_reranking": True},
}

EVALUATOR_MAX_WORKERS = 2
EVALUATOR_MAX_RETRIES = 8
EVALUATOR_TIMEOUT_SECONDS = 300

METRIC_NAMES = [
    "faithfulness",
    "answer_relevancy",
    "context_recall",
    "context_precision",
]

# Tên cột ragas trả về không trùng tên metric trong báo cáo.
METRIC_COLUMNS = {
    "faithfulness": "faithfulness",
    "answer_relevancy": "answer_relevancy",
    "context_recall": "context_recall",
    "context_precision": "llm_context_precision_with_reference",
}


def answer_question(query: str, use_reranking: bool) -> tuple[str, list[str], float]:
    """Sinh câu trả lời với một retrieval strategy cụ thể. Trả (answer, contexts, latency)."""
    started = time.perf_counter()
    chunks = retrieve(query, top_k=TOP_K, use_reranking=use_reranking)
    if not chunks:
        return REFUSAL, [], time.perf_counter() - started

    context = format_context(reorder_for_llm(chunks))
    try:
        answer = call_llm(SYSTEM_PROMPT, f"Context:\n{context}\n\nQuestion: {query}")
    except Exception as error:
        print(f"  LLM error: {error}")
        answer = REFUSAL

    contexts = [chunk["content"] for chunk in chunks]
    return answer or REFUSAL, contexts, time.perf_counter() - started


def build_samples(golden: list[dict], use_reranking: bool) -> list[dict]:
    rows = []
    for index, case in enumerate(golden, 1):
        answer, contexts, latency = answer_question(case["question"], use_reranking)
        print(f"  [{index:>2}/{len(golden)}] {latency:5.2f}s  {case['question'][:60]}")
        rows.append(
            {
                "user_input": case["question"],
                "response": answer,
                "retrieved_contexts": contexts,
                "reference": case["expected_answer"],
                "reference_contexts": [case["expected_context"]],
                "latency_seconds": latency,
            }
        )
    return rows


class _PipelineEmbeddings:
    """Adapter LangChain-style, dùng lại chính `embed_texts()` của Task 4.

    `ResponseRelevancy` cần interface `embed_query`/`embed_documents`. Bọc lại
    model đã nạp sẵn thay vì để ragas load bge-m3 thêm một bản thứ hai (~2,3 GB).
    """

    def embed_query(self, text: str) -> list[float]:
        return embed_texts([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return embed_texts(list(texts))

    async def aembed_query(self, text: str) -> list[float]:
        return self.embed_query(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)


def _evaluator():
    """Evaluator LLM + embeddings cho ragas (dùng chung cho cả hai config)."""
    from google import genai
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import llm_factory

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    llm = llm_factory(
        os.getenv("LLM_MODEL", "gemini-3.6-flash"),
        provider="google",
        client=client,
        max_retries=EVALUATOR_MAX_RETRIES,
    )
    return llm, LangchainEmbeddingsWrapper(_PipelineEmbeddings())


def score_config(rows: list[dict], llm, embeddings) -> dict:
    """Chấm 4 metric bằng ragas."""
    from ragas import EvaluationDataset, evaluate
    from ragas.metrics import (
        Faithfulness,
        LLMContextPrecisionWithReference,
        LLMContextRecall,
        ResponseRelevancy,
    )

    dataset = EvaluationDataset.from_list(
        [{key: row[key] for key in row if key != "latency_seconds"} for row in rows]
    )
    from ragas import RunConfig

    result = evaluate(
        dataset=dataset,
        metrics=[
            Faithfulness(),
            ResponseRelevancy(),
            LLMContextRecall(),
            LLMContextPrecisionWithReference(),
        ],
        llm=llm,
        embeddings=embeddings,
        # Gemini free tier trả 503 khi bị bắn song song; hạ worker và tăng retry
        # để điểm 0 phản ánh chất lượng RAG chứ không phải rate limit.
        run_config=RunConfig(
            max_workers=EVALUATOR_MAX_WORKERS,
            timeout=EVALUATOR_TIMEOUT_SECONDS,
            max_retries=EVALUATOR_MAX_RETRIES,
        ),
    )
    frame = result.to_pandas()
    per_case = {
        name: [
            None if value != value else float(value)
            for value in frame[METRIC_COLUMNS[name]]
        ]
        for name in METRIC_NAMES
        if METRIC_COLUMNS[name] in frame.columns
    }
    averages = {
        name: (
            sum(v for v in values if v is not None)
            / max(len([v for v in values if v is not None]), 1)
        )
        for name, values in per_case.items()
    }
    return {"per_case": per_case, "averages": averages}


def main() -> None:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    print(f"Golden dataset: {len(golden)} cases, top_k={TOP_K}\n")

    llm, embeddings = _evaluator()
    output: dict = {"top_k": TOP_K, "configs": {}}

    for name, settings in CONFIGS.items():
        print(f"=== {name} ({settings}) ===")
        rows = build_samples(golden, settings["use_reranking"])
        scores = score_config(rows, llm, embeddings)
        latencies = [row["latency_seconds"] for row in rows]
        output["configs"][name] = {
            "settings": settings,
            "averages": scores["averages"],
            "per_case": scores["per_case"],
            "questions": [row["user_input"] for row in rows],
            "answers": [row["response"] for row in rows],
            "mean_retrieval_latency": sum(latencies) / len(latencies),
        }
        print(f"  averages: {scores['averages']}\n")

    RAW_RESULTS_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved raw results to {RAW_RESULTS_PATH}")

    print(f"\n{'Metric':<20}{'A dense':>10}{'B hybrid':>10}{'delta':>10}")
    a = output["configs"]["A_dense_only"]["averages"]
    b = output["configs"]["B_hybrid_rrf"]["averages"]
    for name in METRIC_NAMES:
        if name in a and name in b:
            print(f"{name:<20}{a[name]:>10.3f}{b[name]:>10.3f}{b[name] - a[name]:>+10.3f}")


if __name__ == "__main__":
    main()
