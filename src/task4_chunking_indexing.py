"""Load standardized Markdown, chunk it, embed it, and build a Chroma index."""

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

EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024
EMBEDDING_BATCH_SIZE = 16
INDEX_BATCH_SIZE = 128

COLLECTION_NAME = "rag_documents"
_model = None


def _embedding_settings() -> tuple[str, str]:
    load_dotenv(ROOT / ".env")
    provider = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").strip()
    model_name = os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL).strip()
    if provider != "sentence_transformers":
        raise ValueError(
            f"EMBEDDING_PROVIDER={provider!r} chưa được hỗ trợ trong Task 4; "
            "hãy dùng sentence_transformers."
        )
    if not model_name:
        raise ValueError("EMBEDDING_MODEL không được để trống")
    return provider, model_name


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts with the same local model used later for query embedding."""
    global _model
    if not texts:
        return []
    _, model_name = _embedding_settings()
    if _model is None or getattr(_model, "_rag_model_name", None) != model_name:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(model_name)
        _model._rag_model_name = model_name
    vectors = _model.encode(
        texts,
        batch_size=EMBEDDING_BATCH_SIZE,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    if len(vectors) != len(texts):
        raise RuntimeError("Số embedding không khớp số văn bản")
    return vectors.tolist()


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
