"""Run the four required RAGAS metrics on dense and hybrid retrieval."""

import json
from pathlib import Path

from datasets import Dataset
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    Faithfulness,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
    ResponseRelevancy,
)

from .task10_generation import SYSTEM_PROMPT, call_llm, format_context, reorder_for_llm
from .task5_semantic_search import semantic_search
from .task9_retrieval_pipeline import retrieve

ROOT = Path(__file__).parent.parent
DATASET_PATH = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
OUTPUT_PATH = ROOT / "group_project" / "evaluation" / "ragas_results.json"
RECORDS_DIR = ROOT / "group_project" / "evaluation" / "ragas_records"


def build_records(retrieval_mode: str) -> list[dict]:
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = RECORDS_DIR / f"{retrieval_mode}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    records = []
    for case in cases:
        query = case["question"]
        chunks = (
            semantic_search(query, top_k=5)
            if retrieval_mode == "dense"
            else retrieve(query, top_k=5, use_reranking=True)
        )
        context = format_context(reorder_for_llm(chunks))
        response = call_llm(
            SYSTEM_PROMPT,
            f"Context:\n{context}\n\nQuestion: {query}",
        ) if chunks else "Tôi không thể xác minh thông tin này từ nguồn hiện có."
        records.append(
            {
                "user_input": query,
                "response": response,
                "retrieved_contexts": [chunk["content"] for chunk in chunks],
                "reference": case["expected_answer"],
            }
        )
    cache_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return records


def evaluate_records(records: list[dict], llm, embeddings) -> dict:
    dataset = Dataset.from_list(records)
    result = evaluate(
        dataset,
        metrics=[
            Faithfulness(),
            ResponseRelevancy(),
            LLMContextRecall(),
            LLMContextPrecisionWithReference(),
        ],
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=False,
        show_progress=True,
    )
    frame = result.to_pandas()
    return {
        str(key): float(value)
        for key, value in frame.mean(numeric_only=True).to_dict().items()
        if value == value
    }


def main() -> None:
    load_dotenv()
    model = "gpt-4o-mini"
    evaluator = LangchainLLMWrapper(ChatOpenAI(model=model, temperature=0))
    embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))
    output = {
        "generator_model": model,
        "embedding_model": "BAAI/bge-m3",
        "dataset_size": 15,
        "dense": evaluate_records(build_records("dense"), evaluator, embeddings),
        "hybrid": evaluate_records(build_records("hybrid"), evaluator, embeddings),
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
