"""Cấu hình chung cho test: không phụ thuộc .env của máy đang chạy.

Contract test đo đúng "dense + BM25 → RRF một lần → fallback"; cross-encoder
(Task 12) có test riêng và được bật tường minh qua use_cross_encoder=True.
load_dotenv() không ghi đè biến đã có trong os.environ nên đặt ở đây là đủ.
"""

import os

os.environ["RERANKER_ENABLED"] = "0"
