"""
Bonus evaluation — so sánh HyDE và LLM-reranker với baseline hybrid+RRF.

Chạy song song (asyncio + semaphore) để nhanh hơn nhiều lần so với
run_eval.py bản tuần tự. Kết quả lưu ở eval_bonus_results.json.

Chạy: python -m group_project.evaluation.run_eval_bonus
"""

import asyncio
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

from src.bonus_advanced_retrieval import _call_openai, retrieve_hyde, retrieve_llm_reranked
from src.task10_generation import SAFE_REFUSAL, SYSTEM_PROMPT, format_context, reorder_for_llm

GOLDEN_PATH = Path(__file__).parent / "golden_dataset.json"
OUTPUT_PATH = Path(__file__).parent / "eval_bonus_results.json"
EVAL_MODEL = "gpt-4o-mini"
EVAL_EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K = 5
CONCURRENCY = 5

CONFIGS = [("hyde", retrieve_hyde), ("llm_rerank", retrieve_llm_reranked)]


def answer_sync(query: str, top_k: int, retrieve_fn) -> tuple[str, list[str]]:
    chunks = retrieve_fn(query, top_k=top_k)
    if not chunks:
        return SAFE_REFUSAL, []
    context = format_context(reorder_for_llm(chunks))
    user_message = f"Context:\n{context}\n\nQuestion: {query}"
    try:
        answer = _call_openai(SYSTEM_PROMPT, user_message)
    except Exception as error:
        print(f"  generation failed: {error}")
        answer = SAFE_REFUSAL
    return answer, [c["content"] for c in chunks]


def _val(result):
    if isinstance(result, Exception):
        print(f"  metric failed: {result}")
        return None
    return result.value


async def score_row(sem, metrics, item, config_name, retrieve_fn):
    faithfulness, answer_relevancy, context_precision, context_recall = metrics
    async with sem:
        query = item["question"]
        reference = item["expected_answer"]
        answer, contexts = await asyncio.to_thread(answer_sync, query, TOP_K, retrieve_fn)
        ctxs = contexts or ["(không có context nào được truy hồi)"]

        f, ar, cp, cr = await asyncio.gather(
            faithfulness.ascore(user_input=query, response=answer, retrieved_contexts=ctxs),
            answer_relevancy.ascore(user_input=query, response=answer),
            context_precision.ascore(user_input=query, reference=reference, retrieved_contexts=ctxs),
            context_recall.ascore(user_input=query, retrieved_contexts=ctxs, reference=reference),
            return_exceptions=True,
        )
        print(f"[{config_name}] done: {query[:50]}")
        return {
            "question": query,
            "config": config_name,
            "answer": answer,
            "contexts": contexts,
            "faithfulness": _val(f),
            "answer_relevancy": _val(ar),
            "context_precision": _val(cp),
            "context_recall": _val(cr),
        }


async def main() -> None:
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    llm = llm_factory(EVAL_MODEL, client=client)
    embeddings = embedding_factory("openai", model=EVAL_EMBEDDING_MODEL, client=client)
    metrics = (
        Faithfulness(llm=llm),
        AnswerRelevancy(llm=llm, embeddings=embeddings),
        ContextPrecision(llm=llm),
        ContextRecall(llm=llm),
    )

    dataset = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    sem = asyncio.Semaphore(CONCURRENCY)

    tasks = [
        score_row(sem, metrics, item, config_name, retrieve_fn)
        for item in dataset
        for config_name, retrieve_fn in CONFIGS
    ]
    results = await asyncio.gather(*tasks)
    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done: {len(results)} rows -> {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
