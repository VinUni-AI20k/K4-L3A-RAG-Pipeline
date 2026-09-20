"""Chunk the standardized corpus and store stable, embedded chunks in ChromaDB."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .contracts import validate_document

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024
COLLECTION_NAME = "rag_documents"


def _front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Return the small YAML-like header written by task 3, without PyYAML."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, flags=re.DOTALL)
    if not match:
        return {}, text
    values: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator:
            value = value.strip()
            values[key.strip()] = None if value == "null" else value.strip('"')
    return values, text[match.end() :].strip()


def _title(body: str, fallback: str) -> str:
    heading = re.search(r"^#\s+(.+?)\s*$", body, flags=re.MULTILINE)
    return heading.group(1).strip() if heading else fallback.replace("_", " ")


@lru_cache(maxsize=1)
def _embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError("sentence-transformers is required for local embeddings") from error
    return SentenceTransformer(os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL))


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed with the configured local model, cached across indexing and search."""
    if not texts:
        return []
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("texts must contain non-empty strings")
    provider = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").lower()
    if provider != "sentence_transformers":
        raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider}")
    vectors = _embedding_model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [[float(value) for value in vector] for vector in vectors]


def get_collection():
    """Open the persistent Chroma collection configured for cosine distance."""
    try:
        import chromadb
    except ImportError as error:
        raise RuntimeError("chromadb is required to create the vector store") from error
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR)).get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def load_documents() -> list[dict]:
    """Read standardized Markdown files into the shared Document schema."""
    documents: list[dict] = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        header, content = _front_matter(path.read_text(encoding="utf-8").strip())
        if not content:
            continue
        document = {
            "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
            "content": content,
            "metadata": {
                "source": str(header.get("source") or path.name),
                "title": str(header.get("title") or _title(content, path.stem)),
                "doc_type": str(header.get("doc_type") or ("legal" if "legal" in path.parts else "news")),
                "url": header.get("url"),
            },
        }
        validate_document(document)
        documents.append(document)
    return documents


def _split_text(text: str) -> list[str]:
    """Deterministic recursive-style split with a bounded character overlap."""
    parts = [text.strip()]
    for separator in ("\n\n", "\n", ". ", " "):
        next_parts: list[str] = []
        for part in parts:
            if len(part) <= CHUNK_SIZE:
                next_parts.append(part)
                continue
            current = ""
            for piece in part.split(separator):
                candidate = f"{current}{separator if current else ''}{piece}".strip()
                if current and len(candidate) > CHUNK_SIZE:
                    next_parts.append(current)
                    current = piece.strip()
                else:
                    current = candidate
            if current:
                next_parts.append(current)
        parts = next_parts
    chunks: list[str] = []
    for part in parts:
        for start in range(0, len(part), CHUNK_SIZE - CHUNK_OVERLAP):
            piece = part[start : start + CHUNK_SIZE].strip()
            if piece and (not chunks or piece != chunks[-1]):
                chunks.append(piece)
    return chunks


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Split documents into non-empty chunks with stable IDs and metadata."""
    chunks: list[dict] = []
    for document in documents:
        validate_document(document)
        for index, content in enumerate(_split_text(document["content"])):
            chunk = {"id": f"{document['id']}::chunk-{index}", "content": content,
                     "metadata": {**document["metadata"], "chunk_index": index}}
            validate_document(chunk, require_chunk=True)
            chunks.append(chunk)
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Return chunks augmented with an embedding, preserving source metadata."""
    for chunk in chunks:
        validate_document(chunk, require_chunk=True)
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    if len(vectors) != len(chunks):
        raise RuntimeError("embedding provider returned an unexpected vector count")
    return [{**chunk, "embedding": vector} for chunk, vector in zip(chunks, vectors)]


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Idempotently upsert embedded chunks into ChromaDB."""
    if not chunks:
        return
    for chunk in chunks:
        validate_document(chunk, require_chunk=True)
        if not isinstance(chunk.get("embedding"), list):
            raise ValueError("chunk.embedding must be a list")
    # Chroma does not accept None metadata; semantic search restores it to None.
    metadatas = [{key: ("" if key == "url" and value is None else value)
                  for key, value in chunk["metadata"].items()} for chunk in chunks]
    get_collection().upsert(ids=[chunk["id"] for chunk in chunks],
                             documents=[chunk["content"] for chunk in chunks],
                             embeddings=[chunk["embedding"] for chunk in chunks],
                             metadatas=metadatas)


def run_pipeline() -> None:
    embedded_chunks = embed_chunks(chunk_documents(load_documents()))
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks")


if __name__ == "__main__":
    run_pipeline()
