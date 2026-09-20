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

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from .contracts import validate_document


STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

# Keep the code default aligned with .env.example.  This model produces
# 1,536-dimensional vectors, matching EMBEDDING_DIM and the OpenRouter setup.
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIM = 1536

EMBEDDING_BATCH_SIZE = 32

COLLECTION_NAME = "rag_documents"


@lru_cache(maxsize=4)
def _get_sentence_transformer(model_name: str):
    """Load the local model once and reuse it for corpus and query embedding."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def _embedding_settings() -> tuple[str, str]:
    load_dotenv()
    provider = os.getenv("EMBEDDING_PROVIDER", "openrouter").strip().lower()
    model = os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL).strip() or EMBEDDING_MODEL
    return provider, model


def _embed_openai_compatible(client, model_name: str, texts: list[str]) -> list[list[float]]:
    """Embed in bounded batches while preserving the original input order."""
    vectors = []
    total_batches = (len(texts) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
    for batch_number, start in enumerate(
        range(0, len(texts), EMBEDDING_BATCH_SIZE), start=1
    ):
        batch = texts[start:start + EMBEDDING_BATCH_SIZE]
        response = client.embeddings.create(model=model_name, input=batch)
        ordered_data = sorted(response.data, key=lambda item: item.index)
        if len(ordered_data) != len(batch):
            raise ValueError(
                "Embedding provider returned an unexpected vector count "
                f"for batch {batch_number}"
            )
        vectors.extend(item.embedding for item in ordered_data)
        print(f"Embedded batch {batch_number}/{total_batches} ({len(vectors)}/{len(texts)} chunks)")
    return vectors


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts with the provider configured in ``.env``.

    Task 5 imports this function so corpus and query vectors always use the
    same provider and model.
    """
    if not texts:
        return []
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("Every text to embed must be a non-empty string")

    provider, model_name = _embedding_settings()
    if provider == "sentence_transformers":
        vectors = _get_sentence_transformer(model_name).encode(
            texts,
            batch_size=EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > EMBEDDING_BATCH_SIZE,
        )
        return vectors.tolist()

    if provider == "openai":
        from openai import OpenAI

        return _embed_openai_compatible(OpenAI(), model_name, texts)

    if provider == "openrouter":
        from openai import OpenAI

        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required for OpenRouter embeddings")
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        return _embed_openai_compatible(client, model_name, texts)

    if provider == "gemini":
        from google import genai

        client = genai.Client()
        vectors = []
        for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            response = client.models.embed_content(
                model=model_name,
                contents=texts[start:start + EMBEDDING_BATCH_SIZE],
            )
            vectors.extend(embedding.values for embedding in response.embeddings)
        return vectors

    raise ValueError(
        "Unsupported EMBEDDING_PROVIDER. Use sentence_transformers, openai, "
        "openrouter, or gemini."
    )


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
    if not STANDARDIZED_DIR.is_dir():
        raise FileNotFoundError(
            f"Missing standardized corpus directory: {STANDARDIZED_DIR}"
        )

    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        relative_path = path.relative_to(STANDARDIZED_DIR)
        if not relative_path.parts or relative_path.parts[0] not in {"legal", "news"}:
            continue

        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue

        doc_type = relative_path.parts[0]
        title = path.stem.replace("_", " ")
        url = None
        if doc_type == "news":
            lines = content.splitlines()
            if lines and lines[0].startswith("# "):
                title = lines[0][2:].strip() or title
            for line in lines[:12]:
                if line.startswith("**Source:**"):
                    url = line.partition(":**")[2].strip() or None
                    break

        document = {
            "id": relative_path.as_posix(),
            "content": content,
            "metadata": {
                "source": path.name,
                "title": title,
                "doc_type": doc_type,
                "url": url,
            },
        }
        validate_document(document)
        documents.append(document)
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    seen_ids = set()
    for document in documents:
        validate_document(document)
        for index, text in enumerate(splitter.split_text(document["content"])):
            text = text.strip()
            if not text:
                continue
            chunk = {
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index},
            }
            if chunk["id"] in seen_ids:
                raise ValueError(f"Duplicate chunk id: {chunk['id']}")
            validate_document(chunk, require_chunk=True)
            seen_ids.add(chunk["id"])
            chunks.append(chunk)
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    if not chunks:
        return []
    for chunk in chunks:
        validate_document(chunk, require_chunk=True)

    vectors = embed_texts([chunk["content"] for chunk in chunks])
    if len(vectors) != len(chunks):
        raise ValueError("Embedding provider returned an unexpected vector count")

    embedded_chunks = []
    for chunk, vector in zip(chunks, vectors):
        if not vector:
            raise ValueError(f"Empty embedding for chunk {chunk['id']}")
        embedded_chunks.append({**chunk, "embedding": list(vector)})
    return embedded_chunks


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        return

    ids = []
    metadatas = []
    for chunk in chunks:
        validate_document(chunk, require_chunk=True)
        embedding = chunk.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise ValueError(f"Chunk {chunk['id']} has no embedding")
        ids.append(chunk["id"])
        # Chroma metadata values cannot be None. An empty URL is converted
        # back to None by search modules when needed.
        metadatas.append(
            {key: ("" if value is None else value) for key, value in chunk["metadata"].items()}
        )

    if len(ids) != len(set(ids)):
        raise ValueError("Chunk ids must be unique before indexing")

    collection = get_collection()
    collection.upsert(
        ids=ids,
        documents=[chunk["content"] for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        metadatas=metadatas,
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
