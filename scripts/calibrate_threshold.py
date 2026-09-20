"""
Hiệu chỉnh SCORE_THRESHOLD cho Task 9 (Nguyễn Tiến Tuân).

Ý tưởng: chạy dense search trên hai nhóm query, đo cosine similarity cao nhất
của từng query, rồi chọn ngưỡng tách được hai cụm.

    - In-domain      : câu hỏi có câu trả lời trong corpus tuyển sinh đã nạp.
    - Out-of-domain  : câu hỏi ngoài phạm vi, pipeline phải kích hoạt fallback
                       rồi đi tới safe refusal thay vì bịa.

Ngưỡng tốt nằm giữa hai cụm: cao hơn mọi score out-of-domain, thấp hơn mọi
score in-domain. Script quét toàn bộ ngưỡng ứng viên và chọn ngưỡng có biên an
toàn lớn nhất.

Lưu ý: chỉ so sánh với cosine score gốc của dense search, không dùng RRF score.

Chạy:
    python -m scripts.calibrate_threshold
    python -m scripts.calibrate_threshold --out reports/threshold-calibration.md
"""

import argparse
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.task5_semantic_search import semantic_search  # noqa: E402


# Bám sát nội dung thật của 3 văn bản pháp quy + 5 bài tin đã nạp.
IN_DOMAIN = [
    "Thí sinh khu vực 1 được cộng bao nhiêu điểm ưu tiên?",
    "Chỉ tiêu tuyển sinh được xác định theo năng lực đào tạo như thế nào?",
    "Các mốc thời gian quan trọng của kỳ tuyển sinh đại học 2026 là gì?",
    "Thanh toán lệ phí xét tuyển đại học trực tuyến bằng cách nào?",
    "Quy chế tuyển sinh 2026 có những điểm mới nào?",
    "Điều kiện để được xét tuyển thẳng vào đại học là gì?",
    "Cách quy đổi điểm chứng chỉ ngoại ngữ khi xét tuyển?",
    "Ngưỡng đầu vào đối với ngành đào tạo giáo viên được quy định ra sao?",
    "Thí sinh được đăng ký tối đa bao nhiêu nguyện vọng?",
    "Xét tuyển bằng học bạ được quy định thế nào trong quy chế?",
    "Điểm thi đánh giá năng lực được sử dụng để xét tuyển ra sao?",
    "Trách nhiệm của cơ sở đào tạo trong công bố đề án tuyển sinh là gì?",
]

OUT_OF_DOMAIN = [
    "Cách đặt vé máy bay giá rẻ đi Đà Lạt?",
    "Thời tiết Hà Nội ngày mai thế nào?",
    "Điểm chuẩn Đại học Bách Khoa Paris năm nay bao nhiêu?",
    "Công thức nấu phở bò truyền thống?",
    "Giá Bitcoin hôm nay là bao nhiêu?",
    "Cách sửa lỗi màn hình xanh trên Windows 11?",
    "Lịch thi đấu vòng loại World Cup 2026?",
    "Triệu chứng của bệnh cúm A là gì?",
    "Thủ tục đăng ký kết hôn với người nước ngoài?",
    "Nên mua xe máy điện hãng nào tốt nhất?",
]

# Dải ngưỡng quét, theo gợi ý của TEAM-GUIDE (thường rơi vào 0.35 - 0.45).
SWEEP_START, SWEEP_STOP, SWEEP_STEP = 0.20, 0.70, 0.01


def best_dense_score(query: str, top_k: int) -> tuple[float, str]:
    """Trả về cosine score cao nhất và nguồn của chunk top-1."""
    results = semantic_search(query, top_k=top_k)
    if not results:
        return 0.0, "-"
    top = results[0]
    return float(top["score"]), str(top["metadata"].get("source", "-"))


def measure(queries: list[str], top_k: int) -> list[tuple[str, float, str]]:
    rows = []
    for query in queries:
        score, source = best_dense_score(query, top_k)
        rows.append((query, score, source))
        print(f"  {score:6.4f}  {query[:58]:60s} {source[:34]}")
    return rows


def sweep(in_scores: list[float], out_scores: list[float]) -> list[dict]:
    """Quét ngưỡng, đếm lỗi hai phía và đo biên an toàn."""
    candidates = []
    value = SWEEP_START
    while value <= SWEEP_STOP + 1e-9:
        # In-domain rơi dưới ngưỡng -> fallback thừa (tốn thời gian, hạ precision).
        false_fallback = sum(1 for score in in_scores if score < value)
        # Out-of-domain vượt ngưỡng -> không fallback, bot dễ bịa.
        missed_refusal = sum(1 for score in out_scores if score >= value)
        candidates.append(
            {
                "threshold": round(value, 2),
                "false_fallback": false_fallback,
                "missed_refusal": missed_refusal,
                "errors": false_fallback + missed_refusal,
                # Biên: khoảng cách tới điểm gần nhất của cả hai cụm.
                "margin": round(
                    min(
                        [abs(score - value) for score in in_scores + out_scores] or [0.0]
                    ),
                    4,
                ),
            }
        )
        value += SWEEP_STEP
    return candidates


def recommend(candidates: list[dict]) -> dict:
    """Ít lỗi nhất; hoà thì lấy ngưỡng có biên rộng nhất."""
    fewest = min(item["errors"] for item in candidates)
    tied = [item for item in candidates if item["errors"] == fewest]
    return max(tied, key=lambda item: item["margin"])


def markdown(in_rows, out_rows, best, gap) -> str:
    lines = ["# Hiệu chỉnh SCORE_THRESHOLD", "", "## In-domain", "", "| Score | Query | Nguồn top-1 |", "|---:|---|---|"]
    lines += [f"| {s:.4f} | {q} | `{src}` |" for q, s, src in in_rows]
    lines += ["", "## Out-of-domain", "", "| Score | Query | Nguồn top-1 |", "|---:|---|---|"]
    lines += [f"| {s:.4f} | {q} | `{src}` |" for q, s, src in out_rows]
    lines += [
        "",
        "## Kết luận",
        "",
        f"- In-domain: min `{min(s for _, s, _ in in_rows):.4f}`, "
        f"trung vị `{statistics.median([s for _, s, _ in in_rows]):.4f}`",
        f"- Out-of-domain: max `{max(s for _, s, _ in out_rows):.4f}`, "
        f"trung vị `{statistics.median([s for _, s, _ in out_rows]):.4f}`",
        f"- Khoảng trống giữa hai cụm: `{gap:.4f}`",
        f"- **SCORE_THRESHOLD đề xuất: `{best['threshold']}`** "
        f"(fallback thừa: {best['false_fallback']}, bỏ sót refusal: {best['missed_refusal']}, "
        f"biên: {best['margin']:.4f})",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Hiệu chỉnh SCORE_THRESHOLD")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--out", type=Path, help="Ghi bảng kết quả ra file Markdown")
    args = parser.parse_args()

    try:
        semantic_search("kiểm tra kết nối", top_k=1)
    except NotImplementedError:
        print("Task 4/5 chưa implement — chưa calibrate được.")
        print("Cần Vũ hoàn thành task4_chunking_indexing + task5_semantic_search,")
        print("rồi chạy: python -m src.task4_chunking_indexing")
        return 1
    except Exception as error:
        print(f"Không chạy được semantic_search: {type(error).__name__}: {error}")
        print("Kiểm tra chroma_db/ đã được build bằng python -m src.task4_chunking_indexing chưa.")
        return 1

    print(f"\nIN-DOMAIN ({len(IN_DOMAIN)} query)")
    in_rows = measure(IN_DOMAIN, args.top_k)
    print(f"\nOUT-OF-DOMAIN ({len(OUT_OF_DOMAIN)} query)")
    out_rows = measure(OUT_OF_DOMAIN, args.top_k)

    in_scores = [score for _, score, _ in in_rows]
    out_scores = [score for _, score, _ in out_rows]
    gap = min(in_scores) - max(out_scores)

    print("\n" + "=" * 72)
    print(f"In-domain     : min={min(in_scores):.4f}  median={statistics.median(in_scores):.4f}  max={max(in_scores):.4f}")
    print(f"Out-of-domain : min={min(out_scores):.4f}  median={statistics.median(out_scores):.4f}  max={max(out_scores):.4f}")
    print(f"Khoảng trống  : {gap:+.4f}", "(hai cụm tách rời)" if gap > 0 else "(HAI CỤM CHỒNG NHAU)")

    candidates = sweep(in_scores, out_scores)
    best = recommend(candidates)

    print("\nQuét ngưỡng (chỉ in vùng đáng quan tâm):")
    print(f"  {'ngưỡng':>7}  {'fallback thừa':>13}  {'sót refusal':>11}  {'tổng lỗi':>8}")
    for item in candidates:
        if item["errors"] <= min(c["errors"] for c in candidates) + 1:
            mark = " <-- đề xuất" if item["threshold"] == best["threshold"] else ""
            print(f"  {item['threshold']:7.2f}  {item['false_fallback']:13d}  {item['missed_refusal']:11d}  {item['errors']:8d}{mark}")

    print(f"\n>>> SCORE_THRESHOLD={best['threshold']}  (biên an toàn {best['margin']:.4f})")
    print(">>> Điền giá trị này vào .env rồi ghi vào báo cáo cá nhân.")

    if gap <= 0:
        print("\nCẢNH BÁO: hai cụm chồng nhau, không có ngưỡng nào tách sạch.")
        print("Xem lại chất lượng chunking hoặc embedding model trước khi chốt.")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(markdown(in_rows, out_rows, best, gap), encoding="utf-8")
        print(f"\nĐã ghi bảng kết quả: {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
