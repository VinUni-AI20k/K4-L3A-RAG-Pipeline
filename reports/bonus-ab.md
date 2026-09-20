# A/B bonus: HyDE và Cross-encoder Reranker

Bộ đo: 12 query có nhãn, top_k=5, fallback tắt để chỉ so retrieval.

| Config | Hit@1 | Hit@3 | MRR | Δ MRR vs B | Thời gian |
|---|---:|---:|---:|---:|---:|
| A. Dense-only | 83.33% | 100.00% | 0.9167 | +0.0556 | 44.1s |
| B. Hybrid + RRF | 75.00% | 100.00% | 0.8611 | +0.0000 | 27.7s |
| C. B + Reranker | — | — | — | — | KHÔNG ĐO ĐƯỢC |
| D. B + HyDE | 91.67% | 100.00% | 0.9444 | +0.0833 | 56.3s |

> **C. B + Reranker không đo được**: reranker lỗi nên pipeline rơi về thứ tự RRF, số đo sẽ trùng B một cách giả tạo. Lỗi: `HTTPError: 403 Client Error: Forbidden for url: https://api.jina.ai/v1/rerank`

## Hạng của tài liệu đúng theo từng query

| Query | A. Dense-only | B. Hybrid + RRF | C. B + Reranker | D. B + HyDE |
|---|---|---|---|---|
| Thí sinh khu vực 1 được cộng bao nhiêu điểm ưu tiên? | 1 | 1 | 1 | 1 |
| Chỉ tiêu tuyển sinh được xác định theo năng lực đào tạo như thế nào? | 2 | 1 | 1 | 1 |
| Các mốc thời gian quan trọng của kỳ tuyển sinh đại học 2026? | 1 | 1 | 1 | 1 |
| Thanh toán lệ phí xét tuyển đại học trực tuyến bằng cách nào? | 1 | 1 | 1 | 1 |
| Quy chế tuyển sinh 2026 có những điểm mới nào? | 2 | 3 | 3 | 3 |
| Điều kiện để được xét tuyển thẳng vào đại học là gì? | 1 | 1 | 1 | 1 |
| Cách quy đổi điểm chứng chỉ ngoại ngữ khi xét tuyển? | 1 | 1 | 1 | 1 |
| Thí sinh được đăng ký tối đa bao nhiêu nguyện vọng? | 1 | 1 | 1 | 1 |
| Chính sách ưu tiên theo đối tượng được quy định ra sao? | 1 | 1 | 1 | 1 |
| Trách nhiệm công bố đề án tuyển sinh của cơ sở đào tạo? | 1 | 2 | 2 | 1 |
| kv1 cộng mấy điểm | 1 | 1 | 1 | 1 |
| lệ phí xét tuyển nộp sao | 1 | 2 | 2 | 1 |
