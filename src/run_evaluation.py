"""
Evaluation A/B bằng RAGAS.

Hai config chỉ khác nhau ở retrieval strategy, mọi thứ còn lại giữ nguyên:
    Config A — dense-only   : retrieve(..., use_reranking=False)
    Config B — hybrid + RRF : retrieve(..., use_reranking=True)
Cùng golden dataset, cùng generator, cùng SYSTEM_PROMPT của Task 10, cùng top_k.

Bốn metric: faithfulness, answer relevance, context recall, context precision.
Evaluator LLM dùng provider trong .env; evaluator embeddings dùng chính model
local của Task 4 để không tốn thêm chi phí API và không lệch ngôn ngữ.

Chạy:
    python -m src.run_evaluation
Kết quả ghi ra group_project/evaluation/evaluation_runs.json để đối chiếu lại.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from .task4_chunking_indexing import EMBEDDING_MODEL, embed_texts
from .task9_retrieval_pipeline import SCORE_THRESHOLD, retrieve
from .task10_generation import (
    LLM_MODEL,
    LLM_PROVIDER,
    SYSTEM_PROMPT,
    TOP_K,
    call_llm,
    format_context,
    reorder_for_llm,
)


load_dotenv()

ROOT = Path(__file__).parent.parent
EVALUATION_DIR = ROOT / "group_project" / "evaluation"
GOLDEN_PATH = EVALUATION_DIR / "golden_dataset.json"
OOD_PATH = EVALUATION_DIR / "golden_dataset_out_of_domain.json"
RUNS_PATH = EVALUATION_DIR / "evaluation_runs.json"

CONFIGS = {
    "A_dense_only": False,
    "B_hybrid_rrf": True,
}

REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."
# Gemini free tier giới hạn request/phút, chạy song song nhiều sẽ bị 429.
MAX_WORKERS = 2


def build_evaluator_llm():
    """LLM chấm điểm, dùng đúng provider đã cấu hình trong .env."""
    from ragas.llms import LangchainLLMWrapper

    if LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return LangchainLLMWrapper(
            ChatGoogleGenerativeAI(
                model=LLM_MODEL,
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0,
            )
        )

    if LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI

        return LangchainLLMWrapper(ChatOpenAI(model=LLM_MODEL, temperature=0))

    raise ValueError(
        f"Chưa hỗ trợ evaluator cho LLM_PROVIDER={LLM_PROVIDER}. "
        "Cài thêm integration langchain tương ứng."
    )


def build_evaluator_embeddings():
    """Bọc embed_texts() của Task 4 thành embeddings cho RAGAS."""
    from langchain_core.embeddings import Embeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper

    class LocalEmbeddings(Embeddings):
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return embed_texts(texts)

        def embed_query(self, text: str) -> list[float]:
            return embed_texts([text])[0]

    return LangchainEmbeddingsWrapper(LocalEmbeddings())


def answer_with(query: str, use_reranking: bool, top_k: int) -> tuple[str, list[dict]]:
    """Sinh câu trả lời theo đúng luồng Task 10 nhưng ép một retrieval strategy."""
    chunks = retrieve(query, top_k=top_k, use_reranking=use_reranking)
    if not chunks:
        return REFUSAL, []

    context = format_context(reorder_for_llm(chunks))
    answer = call_llm(SYSTEM_PROMPT, f"Context:\n{context}\n\nQuestion: {query}")
    return answer, chunks


def collect_samples(cases: list[dict], use_reranking: bool, top_k: int) -> list[dict]:
    """Chạy pipeline cho từng câu hỏi và gom dữ liệu cho RAGAS."""
    samples = []
    for order, case in enumerate(cases, 1):
        question = case["question"]
        answer, chunks = answer_with(question, use_reranking, top_k)
        print(f"  [{order}/{len(cases)}] {question[:60]}… → {len(chunks)} đoạn")
        samples.append(
            {
                "user_input": question,
                "response": answer,
                "retrieved_contexts": [chunk["content"] for chunk in chunks],
                "reference": case["expected_answer"],
                "reference_contexts": [case["expected_context"]],
            }
        )
    return samples


def score(samples: list[dict], evaluator_llm, evaluator_embeddings) -> dict:
    """Chấm 4 metric trên một config."""
    from ragas import EvaluationDataset, RunConfig, evaluate
    from ragas.metrics import (
        Faithfulness,
        LLMContextPrecisionWithReference,
        LLMContextRecall,
        ResponseRelevancy,
    )

    dataset = EvaluationDataset.from_list(samples)
    result = evaluate(
        dataset=dataset,
        metrics=[
            Faithfulness(),
            ResponseRelevancy(),
            LLMContextRecall(),
            LLMContextPrecisionWithReference(),
        ],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
        run_config=RunConfig(max_workers=MAX_WORKERS),
        show_progress=True,
    )
    return {"summary": result._repr_dict, "per_case": result.to_pandas().to_dict("records")}


def calibrate_threshold(cases: list[dict], ood_cases: list[dict], top_k: int) -> dict:
    """Đo dense score in-domain và out-of-domain để chọn ngưỡng fallback."""
    from .task5_semantic_search import semantic_search

    def best_scores(questions: list[str]) -> list[float]:
        scores = []
        for question in questions:
            hits = semantic_search(question, top_k=1)
            scores.append(hits[0]["score"] if hits else 0.0)
        return scores

    in_domain = best_scores([case["question"] for case in cases])
    out_domain = best_scores([case["question"] for case in ood_cases])
    return {
        "in_domain_min": min(in_domain),
        "in_domain_mean": sum(in_domain) / len(in_domain),
        "out_of_domain_max": max(out_domain) if out_domain else None,
        "out_of_domain_mean": (sum(out_domain) / len(out_domain)) if out_domain else None,
        "suggested_threshold": round(
            (min(in_domain) + max(out_domain)) / 2, 3
        ) if out_domain else None,
        "current_threshold": SCORE_THRESHOLD,
    }


def main() -> None:
    cases = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    ood_cases = (
        json.loads(OOD_PATH.read_text(encoding="utf-8")) if OOD_PATH.exists() else []
    )
    print(f"Golden dataset: {len(cases)} case in-domain, {len(ood_cases)} out-of-domain")
    print(f"Generator: {LLM_PROVIDER} · {LLM_MODEL} | top_k={TOP_K}")

    evaluator_llm = build_evaluator_llm()
    evaluator_embeddings = build_evaluator_embeddings()

    runs = {
        "evaluation_date": date.today().isoformat(),
        "generator": {"provider": LLM_PROVIDER, "model": LLM_MODEL},
        "embedding_model": EMBEDDING_MODEL,
        "top_k": TOP_K,
        "golden_dataset_size": len(cases),
        "configs": {},
    }

    for name, use_reranking in CONFIGS.items():
        print(f"\n=== {name} (use_reranking={use_reranking}) ===")
        samples = collect_samples(cases, use_reranking, TOP_K)
        print("  Đang chấm điểm bằng RAGAS...")
        runs["configs"][name] = score(samples, evaluator_llm, evaluator_embeddings)
        print(f"  {name}: {runs['configs'][name]['summary']}")

    print("\n=== Hiệu chỉnh threshold ===")
    runs["threshold_calibration"] = calibrate_threshold(cases, ood_cases, TOP_K)
    print(json.dumps(runs["threshold_calibration"], ensure_ascii=False, indent=2))

    RUNS_PATH.write_text(json.dumps(runs, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nĐã ghi kết quả: {RUNS_PATH}")


if __name__ == "__main__":
    if (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    main()
