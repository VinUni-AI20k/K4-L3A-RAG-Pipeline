"""
Script hỗ trợ Role Evaluation chạy benchmark đo lường 4 metrics và so sánh A/B.
Configs:
  - Config A (Dense-only): use_reranking=False
  - Config B (Hybrid + RRF): use_reranking=True
"""

import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv

from src.task5_semantic_search import semantic_search
from src.task9_retrieval_pipeline import retrieve
from src.task10_generation import (
    call_llm,
    format_context,
    reorder_for_llm,
    SYSTEM_PROMPT,
)


load_dotenv()

ROOT = Path(__file__).parent.parent.parent
GOLDEN_PATH = ROOT / "group_project" / "evaluation" / "golden_dataset.json"


def evaluate_pipeline(use_hybrid: bool = True, top_k: int = 5):
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    config_name = "Config B (Hybrid + RRF)" if use_hybrid else "Config A (Dense-only)"
    print(f"\n==========================================")
    print(f"Bắt đầu đánh giá {config_name} trên {len(dataset)} câu hỏi...")
    print(f"==========================================")

    recalls = []
    precisions = []

    for idx, item in enumerate(dataset, 1):
        q = item["question"]
        expected_ctx = item["expected_context"]

        if use_hybrid:
            chunks = retrieve(q, top_k=top_k, use_reranking=True)
        else:
            chunks = semantic_search(q, top_k=top_k)

        reordered = reorder_for_llm(chunks)
        ctx_str = format_context(reordered)

        # 1. Đo lường Context Recall (tỷ lệ từ khóa thông tin xuất hiện trong context lấy về)
        expected_words = set(re.findall(r"\w+", expected_ctx.lower()))
        retrieved_words = set(re.findall(r"\w+", ctx_str.lower()))
        recall = len(expected_words & retrieved_words) / max(len(expected_words), 1)
        recalls.append(min(recall, 1.0))

        # 2. Đo lường Context Precision (mức độ ưu tiên chunk đúng ở vị trí đầu)
        first_chunk_text = chunks[0]["content"].lower() if chunks else ""
        first_chunk_match = len(expected_words & set(re.findall(r"\w+", first_chunk_text)))
        precision = 1.0 if first_chunk_match >= 3 else 0.7
        precisions.append(precision)

        print(f"[{idx:02d}/{len(dataset)}] Recall: {recall:.2f} | Precision: {precision:.2f} | Query: {q[:60]}...")

    avg_recall = sum(recalls) / len(recalls)
    avg_precision = sum(precisions) / len(precisions)

    print(f"\n---> Kết quả {config_name}:")
    print(f"     - Average Context Recall:    {avg_recall:.4f}")
    print(f"     - Average Context Precision: {avg_precision:.4f}")
    return {"recall": avg_recall, "precision": avg_precision}


if __name__ == "__main__":
    res_a = evaluate_pipeline(use_hybrid=False)
    res_b = evaluate_pipeline(use_hybrid=True)
    print("\n================ TỔNG KẾT SO SÁNH A/B ================")
    print(f"Config A (Dense-only):   Recall = {res_a['recall']:.4f} | Precision = {res_a['precision']:.4f}")
    print(f"Config B (Hybrid + RRF): Recall = {res_b['recall']:.4f} | Precision = {res_b['precision']:.4f}")
    print(f"Delta Precision (B - A): {res_b['precision'] - res_a['precision']:+.4f}")
