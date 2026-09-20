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

import json
import math
import os
import re
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").strip().lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "").strip() or {
    "sentence_transformers": "BAAI/bge-m3",
    "openai": "text-embedding-3-small",
    "gemini": "gemini-embedding-001",
}.get(EMBEDDING_PROVIDER, "")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM") or "1024")
EMBEDDING_BATCH_SIZE = 32

COLLECTION_NAME = "rag_documents"


def _front_matter(content: str) -> dict[str, str]:
    """Parse the small YAML-compatible header produced by Task 3."""

    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, separator, raw_value = line.partition(":")
        if not separator:
            continue
        value = raw_value.strip()
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = value.strip('"\'')
        if isinstance(parsed, str) and parsed.strip():
            metadata[key.strip()] = parsed.strip()
    return metadata


@lru_cache(maxsize=1)
def _local_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed documents and queries with the same configured model and dimension."""
    if not texts:
        return []
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("Embedding input must contain non-empty strings")
    if EMBEDDING_DIM <= 0:
        raise ValueError("EMBEDDING_DIM must be positive")

    if EMBEDDING_PROVIDER == "sentence_transformers":
        vectors = _local_model(EMBEDDING_MODEL).encode(
            texts, batch_size=EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True, show_progress_bar=False,
        ).tolist()
    elif EMBEDDING_PROVIDER == "openai":
        from openai import OpenAI

        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")
        vectors = []
        with OpenAI() as client:
            for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
                response = client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=texts[start:start + EMBEDDING_BATCH_SIZE],
                    dimensions=EMBEDDING_DIM, encoding_format="float",
                )
                vectors.extend(item.embedding for item in sorted(response.data, key=lambda item: item.index))
    elif EMBEDDING_PROVIDER == "gemini":
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for Gemini embeddings")
        vectors = []
        with genai.Client(api_key=api_key) as client:
            for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
                response = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=texts[start:start + EMBEDDING_BATCH_SIZE],
                    config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
                )
                vectors.extend(item.values for item in (response.embeddings or []))
    else:
        raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}")

    if len(vectors) != len(texts):
        raise ValueError("Embedding provider returned an incorrect vector count")
    for vector in vectors:
        if vector is None or len(vector) != EMBEDDING_DIM:
            raise ValueError("Embedding dimension does not match EMBEDDING_DIM")
        if not all(math.isfinite(value) for value in vector) or not any(vector):
            raise ValueError("Embedding provider returned a non-finite or zero vector")
    return vectors


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    settings = {
        "hnsw:space": "cosine",
        "embedding_provider": EMBEDDING_PROVIDER,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dim": EMBEDDING_DIM,
    }
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME, metadata=settings, embedding_function=None,
    )
    if any((collection.metadata or {}).get(key) != value for key, value in settings.items()):
        raise ValueError("Chroma collection uses different embedding settings; rebuild it before use")
    return collection


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        relative = path.relative_to(STANDARDIZED_DIR)
        if relative.parts[0] not in {"legal", "news"}:
            continue
        content = path.read_text(encoding="utf-8-sig").strip()
        if not content:
            continue
        front_matter = _front_matter(content)
        heading = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        legacy_source = re.search(r"^\*\*Source:\*\*\s*(https?://\S+)", content, re.MULTILINE)
        source_value = front_matter.get("source") or (
            legacy_source.group(1) if legacy_source else relative.as_posix()
        )
        source_url = source_value if source_value.startswith(("https://", "http://")) else None
        documents.append({
            "id": relative.as_posix(),
            "content": content,
            "metadata": {
                "source": source_value,
                "title": front_matter.get("title") or (
                    heading.group(1).strip() if heading else path.stem
                ),
                "doc_type": front_matter.get("doc_type") or relative.parts[0],
                "url": source_url,
            },
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    if not 0 <= CHUNK_OVERLAP < CHUNK_SIZE:
        raise ValueError("Require 0 <= CHUNK_OVERLAP < CHUNK_SIZE")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    seen = set()
    for document in documents:
        if document["id"] in seen:
            raise ValueError(f"Duplicate document ID: {document['id']}")
        seen.add(document["id"])
        for index, text in enumerate(splitter.split_text(document["content"])):
            if text.strip():
                chunks.append({
                    "id": f"{document['id']}::chunk-{index}",
                    "content": text,
                    "metadata": {**document["metadata"], "chunk_index": index},
                })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    embedded = []
    for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[start:start + EMBEDDING_BATCH_SIZE]
        vectors = embed_texts([chunk["content"] for chunk in batch])
        if len(vectors) != len(batch):
            raise ValueError("Embedding count does not match chunk count")
        embedded.extend({**chunk, "embedding": vector} for chunk, vector in zip(batch, vectors))
    return embedded


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        return
    if len({chunk["id"] for chunk in chunks}) != len(chunks):
        raise ValueError("Chunk IDs must be unique")
    collection = get_collection()
    for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[start:start + EMBEDDING_BATCH_SIZE]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[
                {key: value for key, value in chunk["metadata"].items() if value is not None}
                for chunk in batch
            ],
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
