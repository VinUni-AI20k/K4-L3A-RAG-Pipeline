"""Chunk, embed and persist the standardized corpus in ChromaDB.

This module is the single source of truth for embeddings. Query-time dense
retrieval imports :func:`embed_texts`, preventing model/dimension drift.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

from .contracts import validate_document


load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
STANDARDIZED_DIR = ROOT_DIR / "data" / "standardized"
CHROMA_DIR = ROOT_DIR / "chroma_db"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"
INDEX_BATCH_SIZE = 256
EMBED_BATCH_SIZE = 64

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").strip().lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3").strip() or "BAAI/bge-m3"
EMBEDDING_DIM = 1024  # Dimension of the default BAAI/bge-m3 model.
COLLECTION_NAME = "rag_documents"

_MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\([^)]*\)")
_SOURCE_RE = re.compile(r"^\*\*Source:\*\*\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _batches(items: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


@lru_cache(maxsize=None)
def _sentence_transformer(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


@lru_cache(maxsize=1)
def _openai_client():
    from openai import OpenAI

    return OpenAI()


@lru_cache(maxsize=1)
def _gemini_client():
    from google import genai

    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts with sentence-transformers, OpenAI, or Gemini."""
    if not texts:
        return []
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("all texts to embed must be non-empty strings")

    if EMBEDDING_PROVIDER == "sentence_transformers":
        vectors = _sentence_transformer(EMBEDDING_MODEL).encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return [[float(value) for value in vector] for vector in vectors]

    if EMBEDDING_PROVIDER == "openai":
        response = _openai_client().embeddings.create(model=EMBEDDING_MODEL, input=texts)
        ordered = sorted(response.data, key=lambda item: item.index)
        return [[float(value) for value in item.embedding] for item in ordered]

    if EMBEDDING_PROVIDER == "gemini":
        response = _gemini_client().models.embed_content(model=EMBEDDING_MODEL, contents=texts)
        embeddings = response.embeddings or []
        return [[float(value) for value in item.values] for item in embeddings]

    raise ValueError(
        "Unsupported EMBEDDING_PROVIDER. Use sentence_transformers, openai, or gemini."
    )


def get_collection():
    """Open the persistent Chroma collection configured for cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def _document_metadata(path: Path, content: str) -> dict:
    relative = path.relative_to(STANDARDIZED_DIR)
    doc_type = "legal" if relative.parts[0].lower() == "legal" else "news"
    title_match = _TITLE_RE.search(content)
    source_match = _SOURCE_RE.search(content)
    source_value = source_match.group(1).strip() if source_match else path.name
    url = source_value if source_value.lower().startswith(("http://", "https://")) else None
    return {
        "source": path.name,
        "title": title_match.group(1).strip() if title_match else path.stem,
        "doc_type": doc_type,
        "url": url,
    }


def load_documents() -> list[dict]:
    """Read all standardized Markdown documents in deterministic order."""
    documents: list[dict] = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        document = {
            "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
            "content": content,
            "metadata": _document_metadata(path, content),
        }
        validate_document(document)
        documents.append(document)
    return documents


def _is_navigation_noise(text: str) -> bool:
    """Detect chunks dominated by Markdown navigation links."""
    links = _MARKDOWN_LINK_RE.findall(text)
    if len(links) < 3:
        return False
    non_empty_lines = [line for line in text.splitlines() if line.strip()]
    linked_lines = [line for line in non_empty_lines if _MARKDOWN_LINK_RE.search(line)]
    return bool(non_empty_lines) and len(linked_lines) / len(non_empty_lines) > 0.5


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Recursively split documents and assign stable, continuous chunk IDs."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    chunks: list[dict] = []
    for document in documents:
        validate_document(document)
        kept_texts = [
            text.strip()
            for text in splitter.split_text(document["content"])
            if text.strip() and not _is_navigation_noise(text)
        ]
        for index, text in enumerate(kept_texts):
            chunk = {
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index},
            }
            validate_document(chunk, require_chunk=True)
            chunks.append(chunk)
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Return copies of chunks with embedding vectors attached."""
    if not chunks:
        return []
    vectors: list[list[float]] = []
    for batch in _batches(chunks, EMBED_BATCH_SIZE):
        batch_vectors = embed_texts([chunk["content"] for chunk in batch])
        if len(batch_vectors) != len(batch):
            raise RuntimeError("embedding provider returned a different number of vectors")
        vectors.extend(batch_vectors)
    return [{**chunk, "embedding": vector} for chunk, vector in zip(chunks, vectors)]


def _chroma_metadata(metadata: dict) -> dict:
    # Chroma rejects None. Keep None in Python and sanitize only at persistence.
    return {key: ("" if value is None else value) for key, value in metadata.items()}


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert embedded chunks in batches of 256, preserving stable IDs."""
    if not chunks:
        return
    collection = get_collection()
    for batch in _batches(chunks, INDEX_BATCH_SIZE):
        for chunk in batch:
            validate_document(chunk, require_chunk=True)
            if "embedding" not in chunk or not chunk["embedding"]:
                raise ValueError(f"chunk {chunk['id']} has no embedding")
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[_chroma_metadata(chunk["metadata"]) for chunk in batch],
        )


def run_pipeline() -> None:
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks from {len(documents)} documents")


if __name__ == "__main__":
    run_pipeline()
