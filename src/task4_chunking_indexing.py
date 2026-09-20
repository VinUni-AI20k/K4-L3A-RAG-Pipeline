"""Load standardized Markdown, chunk it, embed it, and build a Chroma index."""

import math
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from .contracts import validate_document


ROOT = Path(__file__).parent.parent
STANDARDIZED_DIR = ROOT / "data" / "standardized"
CHROMA_DIR = ROOT / "chroma_db"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
EMBEDDING_BATCH_SIZE = 16
INDEX_BATCH_SIZE = 128

COLLECTION_NAME = "rag_documents"
_embedding_client = None
_embedding_client_model = None


def _embedding_settings() -> tuple[str, str]:
    load_dotenv(ROOT / ".env")
    provider = os.getenv("EMBEDDING_PROVIDER", "openai").strip().lower()
    model_name = os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL).strip()
    if provider != "openai":
        raise ValueError(
            f"EMBEDDING_PROVIDER={provider!r} chưa được hỗ trợ trong Task 4; "
            "hãy dùng openai."
        )
    if not model_name:
        raise ValueError("EMBEDDING_MODEL không được để trống")
    return provider, model_name


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts with OpenAI's model used later for query embedding."""
    global _embedding_client, _embedding_client_model
    if not texts:
        return []
    _, model_name = _embedding_settings()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Thiếu OPENAI_API_KEY trong file .env để tạo embedding")
    if _embedding_client is None or _embedding_client_model != model_name:
        from openai import OpenAI

        _embedding_client = OpenAI(api_key=api_key)
        _embedding_client_model = model_name
    response = _embedding_client.embeddings.create(model=model_name, input=texts)
    data = sorted(response.data, key=lambda item: item.index)
    vectors = [list(item.embedding) for item in data]
    if len(vectors) != len(texts) or any(len(vector) != EMBEDDING_DIM for vector in vectors):
        raise RuntimeError("Số embedding không khớp số văn bản")
    normalized = []
    for vector in vectors:
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        normalized.append([value / norm for value in vector])
    return normalized


def get_collection():
    """Open the persistent cosine-distance Chroma collection."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_documents() -> list[dict]:
    """Read all standardized Markdown files using the shared Document contract."""
    paths = sorted(STANDARDIZED_DIR.rglob("*.md"))
    if not paths:
        raise FileNotFoundError(f"Không có Markdown trong {STANDARDIZED_DIR}; hãy chạy bước 4")
    documents = []
    for path in paths:
        relative = path.relative_to(STANDARDIZED_DIR)
        content = path.read_text(encoding="utf-8").strip()
        heading = re.search(r"(?m)^# (.+)$", content)
        url_match = re.search(r"(?m)^\*\*Source URL:\*\* (\S+)", content)
        document = {
            "id": relative.as_posix(),
            "content": content,
            "metadata": {
                "source": path.name,
                "title": heading.group(1).strip() if heading else path.stem,
                "doc_type": relative.parts[0],
                "url": url_match.group(1) if url_match else None,
            },
        }
        validate_document(document)
        documents.append(document)
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Split documents recursively with stable IDs and sequential chunk indexes."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for document in documents:
        validate_document(document)
        for index, content in enumerate(splitter.split_text(document["content"])):
            chunk = {
                "id": f"{document['id']}::chunk-{index}",
                "content": content,
                "metadata": {**document["metadata"], "chunk_index": index},
            }
            validate_document(chunk, require_chunk=True)
            chunks.append(chunk)
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Embed in bounded batches to avoid holding all model inputs at once."""
    embedded = []
    for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[start : start + EMBEDDING_BATCH_SIZE]
        vectors = embed_texts([chunk["content"] for chunk in batch])
        for chunk, vector in zip(batch, vectors):
            embedded.append({**chunk, "embedding": vector})
        print(f"Embedded {len(embedded)}/{len(chunks)} chunks", flush=True)
    return embedded


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert stable IDs, then remove stale IDs from earlier corpus versions."""
    collection = get_collection()
    expected_ids = {chunk["id"] for chunk in chunks}
    for start in range(0, len(chunks), INDEX_BATCH_SIZE):
        batch = chunks[start : start + INDEX_BATCH_SIZE]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[
                {key: ("" if value is None else value) for key, value in chunk["metadata"].items()}
                for chunk in batch
            ],
        )
    stale_ids = set(collection.get(include=[])["ids"]) - expected_ids
    if stale_ids:
        collection.delete(ids=sorted(stale_ids))


def run_pipeline() -> None:
    """Load, chunk, embed and index the standardized corpus."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    print(f"Loaded {len(documents)} documents; created {len(chunks)} chunks", flush=True)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks", flush=True)


if __name__ == "__main__":
    run_pipeline()
