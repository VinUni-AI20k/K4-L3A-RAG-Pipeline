"""Load standardized Markdown, split it, embed it, and index it in Chroma."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from .contracts import validate_document


load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
# Tuỳ chọn: git revision trên Hugging Face Hub. Máy có torch < 2.6 (macOS Intel)
# không load được pytorch_model.bin, bge-m3 chỉ có safetensors ở refs/pr/130.
EMBEDDING_MODEL_REVISION = os.getenv("EMBEDDING_MODEL_REVISION", "").strip() or None
# Tuỳ chọn: cpu | mps | cuda. Để trống thì sentence-transformers tự chọn; GPU MPS
# trên macOS Intel giới hạn ~6.7GB nên bge-m3 dễ out-of-memory, khi đó đặt cpu.
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "").strip() or None
EMBEDDING_DIM = 1024  # Default BAAI/bge-m3 dimension.
EMBED_BATCH_SIZE = 32
INDEX_BATCH_SIZE = 100

COLLECTION_NAME = "rag_documents"


@lru_cache(maxsize=1)
def _local_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        EMBEDDING_MODEL, revision=EMBEDDING_MODEL_REVISION, device=EMBEDDING_DEVICE
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed text with the provider configured for both indexing and search."""
    if not texts:
        return []

    provider = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").lower()
    if provider == "sentence_transformers":
        vectors = _local_model().encode(texts, batch_size=EMBED_BATCH_SIZE)
        return vectors.tolist()
    if provider == "openai":
        from openai import OpenAI

        response = OpenAI().embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
    if provider == "gemini":
        from google import genai

        response = genai.Client().models.embed_content(model=EMBEDDING_MODEL, contents=texts)
        return [embedding.values for embedding in response.embeddings]
    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider}")


def get_collection():
    """Open the persistent cosine-distance Chroma collection."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    if collection.metadata.get("hnsw:space") != "cosine":
        raise ValueError(f"Collection {COLLECTION_NAME} must use cosine distance")
    return collection


def _read_markdown(path: Path) -> tuple[dict[str, str], str]:
    """Split the simple key/value front matter written by Task 3 from its body."""
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        raise ValueError(f"Missing front matter: {path}")
    try:
        header, body = raw[4:].split("\n---\n", 1)
    except ValueError as exc:
        raise ValueError(f"Unclosed front matter: {path}") from exc
    metadata = {}
    for line in header.splitlines():
        if ":" not in line:
            raise ValueError(f"Invalid front matter line in {path}: {line}")
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata, body.strip()


def load_documents() -> list[dict]:
    """Read standardized Markdown in stable path order, preserving source metadata."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        metadata, content = _read_markdown(path)
        expected_type = path.relative_to(STANDARDIZED_DIR).parts[0]
        if expected_type not in {"legal", "news"} or metadata.get("doc_type") != expected_type:
            raise ValueError(f"Invalid doc_type for {path}")
        document = {
            "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
            "content": content,
            "metadata": {
                "source": metadata.get("source", ""),
                "title": metadata.get("title", ""),
                "doc_type": metadata["doc_type"],
                "url": metadata.get("url") or None,
            },
        }
        validate_document(document)
        documents.append(document)
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Recursively split each document and preserve its stable identity."""
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
    """Embed chunks in batches without changing the input records."""
    embedded = []
    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start : start + EMBED_BATCH_SIZE]
        vectors = embed_texts([chunk["content"] for chunk in batch])
        if len(vectors) != len(batch):
            raise ValueError("Embedding provider returned the wrong number of vectors")
        embedded.extend({**chunk, "embedding": vector} for chunk, vector in zip(batch, vectors))
    return embedded


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks in bounded batches; Chroma IDs keep repeat runs idempotent."""
    if not chunks:
        return
    collection = get_collection()
    for start in range(0, len(chunks), INDEX_BATCH_SIZE):
        batch = chunks[start : start + INDEX_BATCH_SIZE]
        for chunk in batch:
            validate_document(chunk, require_chunk=True)
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[{**chunk["metadata"], "url": chunk["metadata"]["url"] or ""} for chunk in batch],
        )


def run_pipeline() -> None:
    """Load, split, embed, and index the available corpus."""
    documents = load_documents()
    if not documents:
        raise ValueError(f"No standardized Markdown found in {STANDARDIZED_DIR}")
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks from {len(documents)} documents")


if __name__ == "__main__":
    run_pipeline()
