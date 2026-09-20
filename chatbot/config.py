"""Configuration for the standalone legal chatbot."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
LANDING_LEGAL_DIR = ROOT_DIR / "data" / "landing" / "legal"
STANDARDIZED_LEGAL_DIR = ROOT_DIR / "data" / "standardized" / "legal"
CACHE_DIR = Path(__file__).resolve().parent / ".cache"

# "tfidf" (default): scikit-learn TF-IDF + cosine similarity. Pure Python/C,
#   no model download, no torch - works even when the network can't reach
#   Hugging Face or the OS blocks torch's native DLL (both observed on this
#   machine's Application Control policy during development).
# "fastembed": real multilingual sentence embeddings via ONNX Runtime
#   (no torch either, but downloads a model on first run). Use this on a
#   machine with normal internet access for meaningfully better semantic
#   retrieval than TF-IDF.
EMBEDDING_BACKEND = os.getenv("CHATBOT_EMBEDDING_BACKEND", "tfidf").strip().lower()

EMBEDDING_MODEL = os.getenv(
    "CHATBOT_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

CHUNK_MAX_CHARS = int(os.getenv("CHATBOT_CHUNK_MAX_CHARS", "1200"))
CHUNK_OVERLAP = int(os.getenv("CHATBOT_CHUNK_OVERLAP", "150"))

TOP_K = int(os.getenv("CHATBOT_TOP_K", "5"))
RRF_K = 60

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
    "anthropic": "claude-haiku-4-5-20251001",
}

SYSTEM_PROMPT = (
    "Bạn là trợ lý pháp lý tư vấn hợp đồng mua bán căn hộ chung cư tại Việt Nam.\n"
    "Chỉ trả lời dựa trên phần NGỮ CẢNH được cung cấp bên dưới, không suy diễn "
    "hay bịa thêm quy định không có trong ngữ cảnh.\n"
    "Mỗi nhận định quan trọng phải kèm trích dẫn dạng [Nguồn N] tương ứng với "
    "số thứ tự tài liệu trong ngữ cảnh.\n"
    "Nếu ngữ cảnh không đủ để trả lời chắc chắn, hãy trả lời: "
    '"Tôi không thể xác minh thông tin này từ nguồn hiện có." '
    "và không được bịa đặt."
)

PORT = int(os.getenv("CHATBOT_PORT", "8000"))
