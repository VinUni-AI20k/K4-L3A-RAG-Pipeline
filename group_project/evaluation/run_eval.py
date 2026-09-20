"""
Đánh giá pipeline bằng ragas trên golden_dataset.json.

So sánh 2 cấu hình cùng golden dataset, generator, evaluator, prompt và top_k;
chỉ khác retrieval strategy:
    - Config A: dense-only     (task9.retrieve(..., use_reranking=False))
    - Config B: hybrid + RRF   (task9.retrieve(..., use_reranking=True))

Chạy:
    python -m group_project.evaluation.run_eval

Kết quả thô lưu ở group_project/evaluation/eval_raw_results.json (ghi sau mỗi
câu để không mất tiến độ nếu bị gián đoạn). RESULT.md được tổng hợp thủ công
từ file này.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from openai import AsyncOpenAI
from ragas.embeddings import embedding_factory
from ragas.llms import llm_factory
from ragas.metrics.collections import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness

from src.task9_retrieval_pipeline import retrieve
from src.task10_generation import SAFE_REFUSAL, SYSTEM_PROMPT, call_llm, format_context, reorder_for_llm


GOLDEN_PATH = Path(__file__).parent / "golden_dataset.json"
OUTPUT_PATH = Path(__file__).parent / "eval_raw_results.json"

EVAL_MODEL = "gpt-4o-mini"
EVAL_EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K = 5

CONFIGS = [("dense", False), ("hybrid", True)]


def answer_with_config(query: str, top_k: int, use_reranking: bool) -> dict:
    chunks = retrieve(query, top_k=top_k, use_reranking=use_reranking)
    if not chunks:
        return {"answer": SAFE_REFUSAL, "contexts": []}

    context = format_context(reorder_for_llm(chunks))
    user_message = f"Context:\n{context}\n\nQuestion: {query}"
    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:
        print(f"  call_llm failed: {error}")
        answer = SAFE_REFUSAL
    return {"answer": answer, "contexts": [chunk["content"] for chunk in chunks]}


def safe_score(metric_fn, **kwargs) -> float | None:
    try:
        return metric_fn(**kwargs).value
    except Exception as error:
        print(f"  metric failed: {error}")
        return None


def main() -> None:
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    llm = llm_factory(EVAL_MODEL, client=client)
    embeddings = embedding_factory("openai", model=EVAL_EMBEDDING_MODEL, client=client)

    faithfulness = Faithfulness(llm=llm)
    answer_relevancy = AnswerRelevancy(llm=llm, embeddings=embeddings)
    context_precision = ContextPrecision(llm=llm)
    context_recall = ContextRecall(llm=llm)

    dataset = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    results = json.loads(OUTPUT_PATH.read_text(encoding="utf-8")) if OUTPUT_PATH.exists() else []
    done_questions = {row["question"] for row in results}

    for index, item in enumerate(dataset, 1):
        query = item["question"]
        if query in done_questions:
            print(f"[{index}/{len(dataset)}] skip (already scored): {query[:60]}")
            continue

        reference = item["expected_answer"]
        print(f"[{index}/{len(dataset)}] {query[:70]}")

        row = {"question": query, "reference": reference}
        for config_name, use_reranking in CONFIGS:
            out = answer_with_config(query, TOP_K, use_reranking)
            answer = out["answer"]
            contexts = out["contexts"] or ["(không có context nào được truy hồi)"]

            row[config_name] = {
                "answer": answer,
                "contexts": out["contexts"],
                "faithfulness": safe_score(
                    faithfulness.score, user_input=query, response=answer, retrieved_contexts=contexts
                ),
                "answer_relevancy": safe_score(
                    answer_relevancy.score, user_input=query, response=answer
                ),
                "context_precision": safe_score(
                    context_precision.score, user_input=query, reference=reference, retrieved_contexts=contexts
                ),
                "context_recall": safe_score(
                    context_recall.score, user_input=query, retrieved_contexts=contexts, reference=reference
                ),
            }
        results.append(row)
        OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Done. Saved to", OUTPUT_PATH)


if __name__ == "__main__":
    main()
