"""
Hiệu chỉnh SCORE_THRESHOLD cho fallback của Task 9.

So sánh best dense cosine (score gốc, không phải RRF) của:
- in-domain: 20 câu hỏi golden + vài câu diễn đạt khác,
- out-of-domain: câu hỏi ngoài chủ đề và câu hỏi cận chủ đề nhưng không có
  trong corpus (vd. chính sách của sàn khác).

Threshold được chọn là điểm giữa khoảng cách lớn nhất giữa hai phân bố (tối đa
balanced accuracy). Kết quả lưu ở group_project/evaluation/threshold_calibration.json.

    python -m src.calibrate_threshold
"""

import json
from pathlib import Path

from .task9_retrieval_pipeline import best_dense_score


ROOT = Path(__file__).parent.parent
GOLDEN_PATH = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
OUTPUT_PATH = ROOT / "group_project" / "evaluation" / "threshold_calibration.json"

EXTRA_IN_DOMAIN = [
    "Hàng bị giao sai màu thì có được trả không?",
    "Shopee hoàn tiền về Ví ShopeePay mất bao lâu?",
    "Người bán tự vận chuyển có phải chịu phí hoàn hàng không?",
    "Sản phẩm dễ vỡ cần đóng gói như thế nào khi trả hàng?",
    "Có được bán dao găm trên Shopee không?",
]

OUT_OF_DOMAIN = [
    "Thời tiết Hà Nội hôm nay thế nào?",
    "Công thức nấu phở bò ngon",
    "Ai là tổng thống Mỹ hiện nay?",
    "Cách cài đặt Python trên Windows",
    "Kết quả trận bóng đá Việt Nam tối qua",
    "Giá vàng SJC hôm nay bao nhiêu?",
    "Làm sao để học tiếng Anh nhanh?",
    "Lịch thi đại học năm nay",
    "Viết một bài thơ về mùa thu",
    "Cách chữa đau đầu tại nhà",
]

# Cận chủ đề nhưng không có trong corpus: báo cáo riêng, không dùng để chọn
# threshold (fallback bằng PageIndex trên cùng corpus cũng không trả lời được).
NEAR_DOMAIN = [
    "Chính sách đổi trả của Lazada là gì?",
    "Tiki giao hàng trong bao lâu?",
    "Phí mở gian hàng trên TikTok Shop là bao nhiêu?",
]


def choose_threshold(positives: list[float], negatives: list[float]) -> tuple[float, float]:
    """Trả (threshold, balanced_accuracy) tốt nhất; hoà thì chọn gap rộng nhất."""
    candidates = sorted(set(positives + negatives))
    best = (0.0, -1.0, -1.0)
    for low, high in zip(candidates, candidates[1:]):
        threshold = (low + high) / 2
        true_positive = sum(score >= threshold for score in positives) / len(positives)
        true_negative = sum(score < threshold for score in negatives) / len(negatives)
        accuracy = (true_positive + true_negative) / 2
        if (accuracy, high - low) > (best[1], best[2]):
            best = (threshold, accuracy, high - low)
    return round(best[0], 3), best[1]


def main() -> None:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    groups = {
        "in_domain": [item["question"] for item in golden] + EXTRA_IN_DOMAIN,
        "out_of_domain": OUT_OF_DOMAIN,
        "near_domain": NEAR_DOMAIN,
    }
    scores = {
        name: [{"query": query, "best_dense_score": round(best_dense_score(query), 4)} for query in queries]
        for name, queries in groups.items()
    }
    positives = [item["best_dense_score"] for item in scores["in_domain"]]
    negatives = [item["best_dense_score"] for item in scores["out_of_domain"]]
    threshold, accuracy = choose_threshold(positives, negatives)

    summary = {
        "threshold": threshold,
        "balanced_accuracy": accuracy,
        "in_domain_min": min(positives),
        "in_domain_mean": round(sum(positives) / len(positives), 4),
        "out_of_domain_max": max(negatives),
        "out_of_domain_mean": round(sum(negatives) / len(negatives), 4),
        "near_domain_scores": [item["best_dense_score"] for item in scores["near_domain"]],
    }
    OUTPUT_PATH.write_text(
        json.dumps({"summary": summary, "scores": scores}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for name, items in scores.items():
        print(f"\n{name}:")
        for item in sorted(items, key=lambda value: value["best_dense_score"]):
            print(f"  {item['best_dense_score']:.3f}  {item['query']}")
    print(f"\n{json.dumps(summary, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    main()
