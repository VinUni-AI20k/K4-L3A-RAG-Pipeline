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
    response = client.models.embed_content(
        model=model,
        contents=texts,
    )
    return [e.values for e in response.embeddings]


def _embed_nvidia(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("NVIDIA_API_KEY is not set.")
    base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model = os.getenv("NVIDIA_EMBEDDING_MODEL", "nvidia/nv-embedqa-e5-v5")
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.embeddings.create(
        model=model,
        input=texts,
    )
    return [item.embedding for item in response.data]


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
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def _dispatch_embed(provider: str, texts: list[str]) -> list[list[float]]:
    provider = provider.lower()
    if provider == "gemini":
        return _embed_gemini(texts)
    elif provider == "nvidia":
        return _embed_nvidia(texts)
    elif provider == "openai":
        return _embed_openai(texts)
    elif provider == "sentence_transformers":
        return _embed_sentence_transformers(texts)
    else:
        raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider}")


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Tạo vector embeddings theo EMBEDDING_PROVIDER với cơ chế fallback tự động."""
    provider = os.getenv("EMBEDDING_PROVIDER", "gemini")
    enable_fallback = os.getenv("ENABLE_EMBEDDING_FALLBACK", "true").lower() in ("true", "1", "yes")
    fallback_provider = os.getenv("FALLBACK_EMBEDDING_PROVIDER", "nvidia")

    try:
        return _dispatch_embed(provider, texts)
    except Exception as e:
        if enable_fallback and fallback_provider and fallback_provider.lower() != provider.lower():
            logging.warning(
                f"[WARN] Embedding with '{provider}' failed ({e}). Falling back to '{fallback_provider}'..."
            )
            return _dispatch_embed(fallback_provider, texts)
        raise


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    # TODO: Tạo hoặc mở persistent collection.
    #
    # import chromadb
    # CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    # client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    # return client.get_or_create_collection(
    #     name=COLLECTION_NAME,
    #     metadata={"hnsw:space": "cosine"},
    # )
    raise NotImplementedError("Implement get_collection")


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    # TODO: Đọc mọi .md và tạo Document theo contract.
    #
    # documents = []
    # for path in STANDARDIZED_DIR.rglob("*.md"):
    #     doc_type = "legal" if "legal" in path.parts else "news"
    #     documents.append({
    #         "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
    #         "content": path.read_text(encoding="utf-8"),
    #         "metadata": {
    #             "source": path.name,
    #             "title": path.stem,
    #             "doc_type": doc_type,
    #             "url": None,
    #         },
    #     })
    # return documents
    raise NotImplementedError("Implement load_documents")


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    # TODO: Chunk bằng RecursiveCharacterTextSplitter.
    #
    # from langchain_text_splitters import RecursiveCharacterTextSplitter
    # splitter = RecursiveCharacterTextSplitter(
    #     chunk_size=CHUNK_SIZE,
    #     chunk_overlap=CHUNK_OVERLAP,
    #     separators=["\n\n", "\n", ". ", " ", ""],
    # )
    # chunks = []
    # for document in documents:
    #     for index, text in enumerate(splitter.split_text(document["content"])):
    #         chunks.append({
    #             "id": f"{document['id']}::chunk-{index}",
    #             "content": text,
    #             "metadata": {**document["metadata"], "chunk_index": index},
    #         })
    # return chunks
    raise NotImplementedError("Implement chunk_documents")


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    # TODO: Embed theo batch và giữ nguyên các field của chunk.
    #
    # vectors = embed_texts([chunk["content"] for chunk in chunks])
    # for chunk, vector in zip(chunks, vectors):
    #     chunk["embedding"] = vector
    # return chunks
    raise NotImplementedError("Implement embed_chunks")


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    # TODO: Upsert ids, documents, embeddings và metadatas.
    #
    # collection = get_collection()
    # collection.upsert(
    #     ids=[chunk["id"] for chunk in chunks],
    #     documents=[chunk["content"] for chunk in chunks],
    #     embeddings=[chunk["embedding"] for chunk in chunks],
    #     metadatas=[chunk["metadata"] for chunk in chunks],
    # )
    raise NotImplementedError("Implement index_to_vectorstore")


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks")


if __name__ == "__main__":
    run_pipeline()
