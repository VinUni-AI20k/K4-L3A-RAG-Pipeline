"""Task 4: load, chunk, embed, and index standardized documents."""

import os
from pathlib import Path

from dotenv import load_dotenv

from src.contracts import validate_document


ROOT_DIR = Path(__file__).parent.parent
STANDARDIZED_DIR = ROOT_DIR / "data" / "standardized"
CHROMA_DIR = ROOT_DIR / "chroma_db"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024
EMBEDDING_BATCH_SIZE = 32
INDEX_BATCH_SIZE = 100

COLLECTION_NAME = "rag_documents"

_LOCAL_MODEL = None


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts using the provider configured in ``EMBEDDING_PROVIDER``."""
    if not texts:
        return []

    load_dotenv(ROOT_DIR / ".env")
    provider = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").strip().lower()
    model_name = os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL).strip() or EMBEDDING_MODEL

    if provider == "sentence_transformers":
        global _LOCAL_MODEL
        if _LOCAL_MODEL is None:
            from sentence_transformers import SentenceTransformer

            _LOCAL_MODEL = SentenceTransformer(model_name)
        return _LOCAL_MODEL.encode(
            texts,
            batch_size=EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > EMBEDDING_BATCH_SIZE,
        ).tolist()

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.embeddings.create(model=model_name, input=texts)
        return [item.embedding for item in response.data]

    if provider == "gemini":
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.embed_content(
            model=model_name,
            contents=texts,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        return [embedding.values for embedding in response.embeddings]

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider}")


def get_collection():
    """Open the persistent Chroma collection using cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _markdown_metadata(path: Path, content: str) -> dict:
    lines = content.splitlines()
    title = next(
        (line.removeprefix("# ").strip() for line in lines if line.startswith("# ")),
        path.stem,
    )
    source_prefix = "**Source:**"
    url = next(
        (line[len(source_prefix):].strip() for line in lines if line.startswith(source_prefix)),
        None,
    )
    relative = path.relative_to(STANDARDIZED_DIR)
    doc_type = relative.parts[0] if relative.parts else "unknown"
    return {
        "source": relative.as_posix(),
        "title": title,
        "doc_type": doc_type,
        "url": url,
    }


def load_documents() -> list[dict]:
    """Read every non-empty standardized Markdown file as a Document."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        relative_path = path.relative_to(STANDARDIZED_DIR).as_posix()
        document = {
            "id": relative_path,
            "content": content,
            "metadata": _markdown_metadata(path, content),
        }
        validate_document(document)
        documents.append(document)
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Split Documents into stable, overlapping recursive chunks."""
    chunks = []
    for document in documents:
        validate_document(document)
        for index, text in enumerate(_split_text(document["content"])):
            chunk = {
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index},
            }
            validate_document(chunk, require_chunk=True)
            chunks.append(chunk)
    return chunks


def _split_text(text: str) -> list[str]:
    """Split text near semantic boundaries while retaining character overlap."""
    parts = []
    start = 0
    text_length = len(text)
    separators = ("\n\n", "\n", ". ", " ")

    while start < text_length:
        hard_end = min(start + CHUNK_SIZE, text_length)
        end = hard_end
        if hard_end < text_length:
            window = text[start:hard_end]
            minimum_break = CHUNK_SIZE // 2
            for separator in separators:
                position = window.rfind(separator, minimum_break)
                if position >= 0:
                    end = start + position + len(separator)
                    break

        part = text[start:end].strip()
        if part:
            parts.append(part)
        if end >= text_length:
            break
        start = max(end - CHUNK_OVERLAP, start + 1)

    return parts


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Return chunk copies with embeddings, processing bounded batches."""
    embedded_chunks = []
    for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[start:start + EMBEDDING_BATCH_SIZE]
        vectors = embed_texts([chunk["content"] for chunk in batch])
        if len(vectors) != len(batch):
            raise ValueError("Embedding provider returned an unexpected vector count")
        embedded_chunks.extend(
            {**chunk, "embedding": vector}
            for chunk, vector in zip(batch, vectors)
        )
    return embedded_chunks


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert embedded chunks into Chroma in deterministic batches."""
    collection = get_collection()
    for start in range(0, len(chunks), INDEX_BATCH_SIZE):
        batch = chunks[start:start + INDEX_BATCH_SIZE]
        metadatas = [
            {key: ("" if value is None else value) for key, value in chunk["metadata"].items()}
            for chunk in batch
        ]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=metadatas,
        )


def run_pipeline() -> None:
    """Run loading, chunking, embedding, and indexing."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks from {len(documents)} documents")


if __name__ == "__main__":
    run_pipeline()
