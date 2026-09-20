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
import time
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
# Dải ngưỡng quét khi hiệu chỉnh fallback, bước 0.01.
THRESHOLD_GRID = [round(0.30 + 0.01 * step, 2) for step in range(46)]
# Gemini free tier giới hạn 15 request/phút cho flash-lite. RAGAS tự retry theo
# RunConfig, nhưng vòng sinh câu trả lời bên dưới thì phải tự hãm tốc.
MAX_WORKERS = 2
MIN_SECONDS_BETWEEN_CALLS = 4.5
MAX_RETRY_ON_QUOTA = 6


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


_last_call_at = 0.0


def call_llm_paced(system_prompt: str, user_message: str) -> str:
    """Gọi LLM nhưng giữ nhịp dưới hạn mức phút và retry khi bị 429."""
    global _last_call_at

    for attempt in range(MAX_RETRY_ON_QUOTA):
        waited = time.monotonic() - _last_call_at
        if waited < MIN_SECONDS_BETWEEN_CALLS:
            time.sleep(MIN_SECONDS_BETWEEN_CALLS - waited)

        _last_call_at = time.monotonic()
        try:
            return call_llm(system_prompt, user_message)
        except Exception as error:
            message = str(error)
            if "429" not in message and "RESOURCE_EXHAUSTED" not in message:
                raise
            # Quota theo NGAY thi cho bao lau cung vo ich, dung ngay de giu lai
            # ket qua config da chay xong thay vi ngu 20 phut roi van that bai.
            if "PerDay" in message:
                raise RuntimeError(
                    "Het quota theo ngay cua model. Doi quota reset, doi key "
                    "hoac bat billing roi chay lai."
                ) from error
            backoff = 60 * (attempt + 1)
            print(f"    429 quota, cho {backoff}s roi thu lai ({attempt + 1}/{MAX_RETRY_ON_QUOTA})")
            time.sleep(backoff)

    raise RuntimeError("Het luot retry vi quota, chua goi duoc LLM")


def answer_with(query: str, use_reranking: bool, top_k: int) -> tuple[str, list[dict]]:
    """Sinh câu trả lời theo đúng luồng Task 10 nhưng ép một retrieval strategy."""
    chunks = retrieve(query, top_k=top_k, use_reranking=use_reranking)
    if not chunks:
        return REFUSAL, []

    context = format_context(reorder_for_llm(chunks))
    answer = call_llm_paced(SYSTEM_PROMPT, f"Context:\n{context}\n\nQuestion: {query}")
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
            # strictness=1: flash-lite khong ho tro multiple candidates, mac dinh
            # strictness=3 se bao 400 INVALID_ARGUMENT.
            ResponseRelevancy(strictness=1),
            LLMContextRecall(),
            LLMContextPrecisionWithReference(),
        ],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
        run_config=RunConfig(max_workers=MAX_WORKERS, timeout=600, max_retries=5),
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

    summary = {
        "in_domain_scores": [round(score, 3) for score in in_domain],
        "out_of_domain_scores": [round(score, 3) for score in out_domain],
        "in_domain_min": round(min(in_domain), 3),
        "in_domain_mean": round(sum(in_domain) / len(in_domain), 3),
        "current_threshold": SCORE_THRESHOLD,
    }
    if not out_domain:
        summary["note"] = "Thiếu câu out-of-domain nên không hiệu chỉnh được."
        return summary

    summary["out_of_domain_max"] = round(max(out_domain), 3)
    summary["out_of_domain_mean"] = round(sum(out_domain) / len(out_domain), 3)
    # Hai phân bố có thể chồng lấn (câu ngoài domain vẫn dùng văn phong hành
    # chính giống văn bản luật), khi đó không ngưỡng nào tách sạch được. Quét cả
    # dải rồi chọn theo kết quả phân loại thay vì lấy điểm giữa hai cực.
    summary["distributions_overlap"] = min(in_domain) < max(out_domain)

    sweep = []
    for step in range(len(THRESHOLD_GRID)):
        threshold = THRESHOLD_GRID[step]
        sweep.append(
            {
                "threshold": threshold,
                "in_domain_false_fallback": sum(1 for s in in_domain if s < threshold),
                "out_of_domain_caught": sum(1 for s in out_domain if s < threshold),
            }
        )
    summary["sweep"] = sweep

    # Ưu tiên bắt được nhiều câu ngoài domain nhất, sau đó ít bắt nhầm nhất.
    best_key = min(
        (-row["out_of_domain_caught"], row["in_domain_false_fallback"]) for row in sweep
    )
    plateau = [
        row["threshold"]
        for row in sweep
        if (-row["out_of_domain_caught"], row["in_domain_false_fallback"]) == best_key
    ]
    best_row = next(row for row in sweep if row["threshold"] == plateau[0])

    summary["optimal_range"] = [plateau[0], plateau[-1]]
    # Lấy giữa vùng tối ưu để có biên an toàn về cả hai phía.
    summary["suggested_threshold"] = round((plateau[0] + plateau[-1]) / 2, 2)
    summary["at_suggested"] = {
        "in_domain_false_fallback": f"{best_row['in_domain_false_fallback']}/{len(in_domain)}",
        "out_of_domain_caught": f"{best_row['out_of_domain_caught']}/{len(out_domain)}",
    }
    return summary


def main() -> None:
    cases = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    ood_cases = (
        json.loads(OOD_PATH.read_text(encoding="utf-8")) if OOD_PATH.exists() else []
    )
    print(f"Golden dataset: {len(cases)} case in-domain, {len(ood_cases)} out-of-domain")
    print(f"Generator: {LLM_PROVIDER} · {LLM_MODEL} | top_k={TOP_K}")

    evaluator_llm = build_evaluator_llm()
    evaluator_embeddings = build_evaluator_embeddings()

    # Chạy lại một config lẻ: `python -m src.run_evaluation B`. Kết quả của
    # config cũ trong file được giữ nguyên, chỉ ghi đè config vừa chạy.
    wanted = [arg.upper() for arg in sys.argv[1:]]
    selected = {
        name: rerank
        for name, rerank in CONFIGS.items()
        if not wanted or any(name.upper().startswith(w) for w in wanted)
    }
    if not selected:
        raise SystemExit(f"Không khớp config nào với {wanted}; có: {list(CONFIGS)}")

    runs = {
        "evaluation_date": date.today().isoformat(),
        "generator": {"provider": LLM_PROVIDER, "model": LLM_MODEL},
        "embedding_model": EMBEDDING_MODEL,
        "top_k": TOP_K,
        "golden_dataset_size": len(cases),
        "configs": {},
    }
    if RUNS_PATH.exists():
        previous = json.loads(RUNS_PATH.read_text(encoding="utf-8"))
        runs["configs"] = previous.get("configs", {})
        runs["previous_run"] = {
            "evaluation_date": previous.get("evaluation_date"),
            "generator": previous.get("generator"),
            "configs": list(previous.get("configs", {})),
        }

    print(f"Chạy config: {list(selected)}")
    for name, use_reranking in selected.items():
        print(f"\n=== {name} (use_reranking={use_reranking}) ===")
        samples = collect_samples(cases, use_reranking, TOP_K)
        print("  Đang chấm điểm bằng RAGAS...")
        runs["configs"][name] = score(samples, evaluator_llm, evaluator_embeddings)
        print(f"  {name}: {runs['configs'][name]['summary']}")
        # Ghi ngay sau mỗi config: nếu config sau lỗi thì vẫn giữ được kết quả
        # của config trước, không phải chạy lại từ đầu.
        RUNS_PATH.write_text(
            json.dumps(runs, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    print("\n=== Hiệu chỉnh threshold ===")
    runs["threshold_calibration"] = calibrate_threshold(cases, ood_cases, TOP_K)
    print(json.dumps(runs["threshold_calibration"], ensure_ascii=False, indent=2))

    RUNS_PATH.write_text(json.dumps(runs, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nĐã ghi kết quả: {RUNS_PATH}")


if __name__ == "__main__":
    if (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    main()
