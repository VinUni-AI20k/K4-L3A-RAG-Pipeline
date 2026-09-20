"""Cấu hình chung cho test: không phụ thuộc .env của máy đang chạy.

Contract test đo đúng "dense + BM25 → RRF một lần → fallback"; cross-encoder
(Task 12) và HyDE (Task 14) có test riêng, bật tường minh qua tham số.
load_dotenv() không ghi đè biến đã có trong os.environ nên đặt ở đây là đủ.
"""

import os

os.environ["RERANKER_ENABLED"] = "0"
os.environ["HYDE_ENABLED"] = "0"
