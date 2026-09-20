"""
A/B đo hiệu quả hai bonus: HyDE và cross-encoder reranker.

Rubric chỉ cho điểm bonus khi "tính năng chạy được VÀ có kết quả đo kiểm chứng",
nên script này đo 4 cấu hình trên cùng một bộ query có nhãn:

    A. Dense-only            (use_reranking=False)
    B. Hybrid + RRF          (baseline của Task 9)
    C. Hybrid + RRF + Reranker   (bonus reranker)
    D. HyDE + Hybrid + RRF       (bonus query expansion)

Nhãn ở đây là "tài liệu nào ĐÁNG LẼ phải xuất hiện", không phải chunk cụ thể —
chunk id phụ thuộc cách chunk của Task 4 nên không ổn định để làm ground truth.

Metric:
    Hit@1 / Hit@3 : tỉ lệ query có tài liệu đúng nằm ở hạng 1 / trong top 3.
    MRR           : 1/hạng của tài liệu đúng đầu tiên, phạt nặng xếp hạng sai.

Chạy:
    python -m scripts.ab_bonus
    python -m scripts.ab_bonus --out reports/bonus-ab.md
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import src.task7_reranking as reranking  # noqa: E402
import src.task9_retrieval_pipeline as pipeline  # noqa: E402


# (query, các mảnh tên file được tính là đúng)
LABELLED: list[tuple[str, tuple[str, ...]]] = [
    ("Thí sinh khu vực 1 được cộng bao nhiêu điểm ưu tiên?",
     ("thong_tu_06", "quyet_dinh_955", "chinh_sach_uu_tien")),
    ("Chỉ tiêu tuyển sinh được xác định theo năng lực đào tạo như thế nào?",
     ("thong_tu_34",)),
    ("Các mốc thời gian quan trọng của kỳ tuyển sinh đại học 2026?",
     ("moc_thoi_gian", "huong_dan_tuyen_sinh")),
    ("Thanh toán lệ phí xét tuyển đại học trực tuyến bằng cách nào?",
     ("thanh_toan_truc_tuyen",)),
    ("Quy chế tuyển sinh 2026 có những điểm mới nào?",
     ("diem_moi", "thong_tu_06")),
    ("Điều kiện để được xét tuyển thẳng vào đại học là gì?",
     ("thong_tu_06", "quyet_dinh_955")),
    ("Cách quy đổi điểm chứng chỉ ngoại ngữ khi xét tuyển?",
     ("thong_tu_06", "quyet_dinh_955", "diem_moi")),
    ("Thí sinh được đăng ký tối đa bao nhiêu nguyện vọng?",
     ("thong_tu_06", "quyet_dinh_955", "huong_dan_tuyen_sinh")),
    ("Chính sách ưu tiên theo đối tượng được quy định ra sao?",
     ("chinh_sach_uu_tien", "thong_tu_06", "quyet_dinh_955")),
    ("Trách nhiệm công bố đề án tuyển sinh của cơ sở đào tạo?",
     ("thong_tu_06", "quyet_dinh_955")),
    # Query kiểu thí sinh gõ tắt — đây là chỗ HyDE phải thắng.
    ("kv1 cộng mấy điểm", ("thong_tu_06", "quyet_dinh_955", "chinh_sach_uu_tien")),
    ("lệ phí xét tuyển nộp sao", ("thanh_toan_truc_tuyen",)),
]

CONFIGS = {
    "A. Dense-only":        {"use_reranking": False, "hyde": False, "rerank": False},
    "B. Hybrid + RRF":      {"use_reranking": True,  "hyde": False, "rerank": False},
    "C. B + Reranker":      {"use_reranking": True,  "hyde": False, "rerank": True},
    "D. B + HyDE":          {"use_reranking": True,  "hyde": True,  "rerank": False},
}


def rank_of_hit(results: list[dict], expected: tuple[str, ...]) -> int | None:
    """Hạng (bắt đầu từ 1) của kết quả đầu tiên thuộc tài liệu đúng."""
    for rank, item in enumerate(results, 1):
        source = str(item["metadata"].get("source", "")).lower()
        if any(fragment in source for fragment in expected):
            return rank
    return None


def run_config(name: str, config: dict, top_k: int) -> dict:
    """Chạy toàn bộ query với một cấu hình, trả về metric tổng hợp."""
    # Bật/tắt bonus qua flag module vì signature retrieve() bị contract khoá.
    pipeline.USE_HYDE = config["hyde"]
    pipeline.USE_MODEL_RERANK = config["rerank"]

    hits1 = hits3 = 0
    reciprocal = 0.0
    started = time.monotonic()
    details = []
    failures_before = reranking.RERANK_FAILURES

    for query, expected in LABELLED:
        # score_threshold=0.0 để tắt fallback: đang so retrieval, không so PageIndex.
        results = pipeline.retrieve(
            query, top_k=top_k, score_threshold=0.0,
            use_reranking=config["use_reranking"],
        )
        rank = rank_of_hit(results, expected)
        details.append((query, rank))
        if rank == 1:
            hits1 += 1
        if rank is not None and rank <= 3:
            hits3 += 1
        if rank is not None:
            reciprocal += 1.0 / rank
        print(f"  hạng={rank if rank else '-':>3}  {query[:56]}")

    total = len(LABELLED)
    # Reranker nuốt lỗi và trả lại thứ tự RRF, nên nếu không đếm thì cấu hình
    # hỏng vẫn ra số đẹp và bị đọc nhầm thành "không cải thiện".
    failed = reranking.RERANK_FAILURES - failures_before
    return {
        "name": name,
        "invalid": bool(config["rerank"] and failed),
        "error": reranking.LAST_RERANK_ERROR if failed else "",
        "hit1": hits1 / total,
        "hit3": hits3 / total,
        "mrr": reciprocal / total,
        "seconds": time.monotonic() - started,
        "details": details,
    }


def table(rows: list[dict], baseline: str = "B. Hybrid + RRF") -> list[str]:
    base = next((row for row in rows if row["name"] == baseline), rows[0])
    lines = [
        "| Config | Hit@1 | Hit@3 | MRR | Δ MRR vs B | Thời gian |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        if row.get("invalid"):
            lines.append(
                f"| {row['name']} | — | — | — | — | KHÔNG ĐO ĐƯỢC |"
            )
            continue
        delta = row["mrr"] - base["mrr"]
        lines.append(
            f"| {row['name']} | {row['hit1']:.2%} | {row['hit3']:.2%} | "
            f"{row['mrr']:.4f} | {delta:+.4f} | {row['seconds']:.1f}s |"
        )
    for row in rows:
        if row.get("invalid"):
            lines += ["", f"> **{row['name']} không đo được**: reranker lỗi nên "
                          f"pipeline rơi về thứ tự RRF, số đo sẽ trùng B một cách giả tạo. "
                          f"Lỗi: `{row['error']}`"]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="A/B bonus: HyDE và Reranker")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    try:
        pipeline.semantic_search("kiểm tra kết nối", top_k=1)
    except NotImplementedError:
        print("Task 4/5/6 chưa implement — chưa đo A/B được.")
        print("Cần Vũ hoàn thành, rồi chạy: python -m src.task4_chunking_indexing")
        return 1
    except Exception as error:
        print(f"Không chạy được: {type(error).__name__}: {error}")
        return 1

    original = (pipeline.USE_HYDE, pipeline.USE_MODEL_RERANK)
    rows = []
    try:
        for name, config in CONFIGS.items():
            print(f"\n{name}")
            rows.append(run_config(name, config, args.top_k))
    finally:
        pipeline.USE_HYDE, pipeline.USE_MODEL_RERANK = original

    print("\n" + "=" * 78)
    for line in table(rows):
        print(line)

    base = next(row for row in rows if row["name"] == "B. Hybrid + RRF")
    for row in rows:
        if row.get("invalid"):
            print(f"\n{row['name']}: KHÔNG ĐO ĐƯỢC — reranker lỗi, "
                  f"pipeline dùng thứ tự RRF.\n  Lỗi: {row['error']}")
            continue
        if row["name"].startswith(("C.", "D.")) and row["mrr"] <= base["mrr"]:
            print(f"\nLƯU Ý: {row['name']} KHÔNG cải thiện so với B "
                  f"({row['mrr']:.4f} vs {base['mrr']:.4f}).")
            print("Rubric chỉ cho bonus khi chứng minh được cải thiện — "
                  "báo cáo trung thực số này thay vì tắt bonus đi.")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        body = ["# A/B bonus: HyDE và Cross-encoder Reranker", "",
                f"Bộ đo: {len(LABELLED)} query có nhãn, top_k={args.top_k}, "
                "fallback tắt để chỉ so retrieval.", ""]
        body += table(rows)
        body += ["", "## Hạng của tài liệu đúng theo từng query", "",
                 "| Query | " + " | ".join(row["name"] for row in rows) + " |",
                 "|---" * (len(rows) + 1) + "|"]
        for index, (query, _) in enumerate(LABELLED):
            cells = [str(row["details"][index][1] or "-") for row in rows]
            body.append(f"| {query} | " + " | ".join(cells) + " |")
        args.out.write_text("\n".join(body) + "\n", encoding="utf-8")
        print(f"\nĐã ghi: {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
