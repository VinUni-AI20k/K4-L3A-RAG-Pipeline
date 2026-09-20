"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn.
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng. Task 5 phải dùng chung embed_texts().
"""

from pathlib import Path


STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

COLLECTION_NAME = "rag_documents"

import logging
import os
from dotenv import load_dotenv

load_dotenv()


def _embed_gemini(texts: list[str]) -> list[list[float]]:
    from google import genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
    client = genai.Client(api_key=api_key)
    
    all_embeddings = []
    batch_size = 64
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.models.embed_content(
            model=model,
            contents=batch,
        )
        all_embeddings.extend([e.values for e in response.embeddings])
    return all_embeddings


def _embed_nvidia(texts: list[str], input_type: str = "passage") -> list[list[float]]:
    from openai import OpenAI
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("NVIDIA_API_KEY is not set.")
    base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model = os.getenv("NVIDIA_EMBEDDING_MODEL", "nvidia/nv-embedqa-e5-v5")
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    all_embeddings = []
    batch_size = 64
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            response = client.embeddings.create(
                model=model,
                input=batch,
                extra_body={"input_type": input_type, "truncate": "NONE"},
            )
        except Exception:
            response = client.embeddings.create(
                model=model,
                input=batch,
            )
        all_embeddings.extend([item.embedding for item in response.data])
    return all_embeddings


def _embed_sentence_transformers(texts: list[str]) -> list[list[float]]:
    from sentence_transformers import SentenceTransformer
    model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    model = SentenceTransformer(model_name)
    return model.encode(texts).tolist()


def _embed_openai(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or None
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    all_embeddings = []
    batch_size = 64
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(model=model, input=batch)
        all_embeddings.extend([item.embedding for item in response.data])
    return all_embeddings



def _dispatch_embed(provider: str, texts: list[str], input_type: str = "passage") -> list[list[float]]:
    provider = provider.lower()
    if provider == "gemini":
        return _embed_gemini(texts)
    elif provider == "nvidia":
        return _embed_nvidia(texts, input_type=input_type)
    elif provider == "openai":
        return _embed_openai(texts)
    elif provider == "sentence_transformers":
        return _embed_sentence_transformers(texts)
    else:
        raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider}")


def embed_texts(texts: list[str], input_type: str = "passage") -> list[list[float]]:
    """Tạo vector embeddings theo EMBEDDING_PROVIDER với cơ chế fallback tự động."""
    provider = os.getenv("EMBEDDING_PROVIDER", "gemini")
    enable_fallback = os.getenv("ENABLE_EMBEDDING_FALLBACK", "true").lower() in ("true", "1", "yes")
    fallback_provider = os.getenv("FALLBACK_EMBEDDING_PROVIDER", "nvidia")

    try:
        return _dispatch_embed(provider, texts, input_type=input_type)
    except Exception as e:
        if enable_fallback and fallback_provider and fallback_provider.lower() != provider.lower():
            logging.warning(
                f"[WARN] Embedding with '{provider}' failed ({e}). Falling back to '{fallback_provider}'..."
            )
            return _dispatch_embed(fallback_provider, texts, input_type=input_type)
        raise


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents = []
    if not STANDARDIZED_DIR.exists():
        return documents
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        doc_type = "legal" if "legal" in path.parts else "news"
        documents.append({
            "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
            "content": path.read_text(encoding="utf-8"),
            "metadata": {
                "source": path.name,
                "title": path.stem,
                "doc_type": doc_type,
                "url": None,
            },
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    chunks = []
    for document in documents:
        text = document["content"]
        step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
        start = 0
        index = 0
        while start < len(text):
            end = min(len(text), start + CHUNK_SIZE)
            if end < len(text):
                newline_pos = text.rfind("\n", start, end)
                if newline_pos > start + CHUNK_SIZE // 2:
                    end = newline_pos + 1
                else:
                    space_pos = text.rfind(" ", start, end)
                    if space_pos > start + CHUNK_SIZE // 2:
                        end = space_pos + 1
            chunk_str = text[start:end].strip()
            if chunk_str:
                chunks.append({
                    "id": f"{document['id']}::chunk-{index}",
                    "content": chunk_str,
                    "metadata": {**document["metadata"], "chunk_index": index},
                })
                index += 1
            if end >= len(text):
                break
            start += step
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    if not chunks:
        return []
    vectors = embed_texts([chunk["content"] for chunk in chunks], input_type="passage")
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        return
    collection = get_collection()
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[chunk["metadata"] for chunk in batch],
        )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks")


if __name__ == "__main__":
    run_pipeline()
