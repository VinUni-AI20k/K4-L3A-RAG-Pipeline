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
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = 1024

COLLECTION_NAME = "rag_documents"

_embedding_model: Any = None


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed danh sách văn bản theo provider được cấu hình."""
    if not texts:
        return []
    provider = os.getenv("EMBEDDING_PROVIDER", EMBEDDING_PROVIDER).lower()
    if provider == "openai":
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment or .env file.")
        client = OpenAI(api_key=api_key)
        raw_model = os.getenv("EMBEDDING_MODEL") or "text-embedding-3-small"
        # OpenAI embedding models must be text-embedding-*, not chat models like gpt-4o-mini
        model = "text-embedding-3-small" if "gpt" in raw_model.lower() else raw_model

        # OpenAI supports batch embedding up to 2048 inputs per request
        results: list[list[float]] = []
        batch_size = 128
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = client.embeddings.create(input=batch, model=model)
            results.extend([item.embedding for item in response.data])
        return results
    elif provider == "gemini":
        from google import genai

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        model = os.getenv("EMBEDDING_MODEL") or "text-embedding-004"
        results = []
        for text in texts:
            resp = client.models.embed_content(model=model, contents=text)
            results.append(resp.embedding.values)
        return results
    else:  # sentence_transformers
        global _embedding_model
        if _embedding_model is None:
            from sentence_transformers import SentenceTransformer

            model_name = os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL)
            _embedding_model = SentenceTransformer(model_name)
        embeddings = _embedding_model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _parse_markdown_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    metadata: dict[str, Any] = {}
    content = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            import yaml

            try:
                metadata = yaml.safe_load(parts[1]) or {}
                content = parts[2].strip()
            except Exception:
                pass

    doc_type = metadata.get("doc_type") or ("legal" if "legal" in path.parts else "news")
    source = metadata.get("source") or path.name
    title = metadata.get("title") or path.stem
    url = metadata.get("url")

    return {
        "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
        "content": content,
        "metadata": {
            "source": source,
            "title": title,
            "doc_type": doc_type,
            "url": url if url else None,
        },
    }


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents: list[dict] = []
    if not STANDARDIZED_DIR.exists():
        return documents

    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        if path.is_file() and not path.name.startswith("."):
            doc = _parse_markdown_file(path)
            if doc["content"].strip():
                documents.append(doc)
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "Điều ", "Khoản ", ". ", " ", ""],
    )
    chunks: list[dict] = []
    for document in documents:
        splits = splitter.split_text(document["content"])
        chunk_idx = 0
        for text in splits:
            chunk_text = text.strip()
            if not chunk_text:
                continue
            chunk_metadata = dict(document["metadata"])
            chunk_metadata["chunk_index"] = chunk_idx
            chunks.append({
                "id": f"{document['id']}::chunk-{chunk_idx}",
                "content": chunk_text,
                "metadata": chunk_metadata,
            })
            chunk_idx += 1
    return chunks


def embed_chunks(chunks: list[dict], batch_size: int = 32) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    if not chunks:
        return []
    texts = [chunk["content"] for chunk in chunks]
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings.extend(embed_texts(batch))

    for chunk, vector in zip(chunks, embeddings):
        chunk["embedding"] = vector
    return chunks


def _sanitize_metadata_for_chroma(metadata: dict) -> dict:
    """Chuyển None thành chuỗi rỗng để tương thích ChromaDB."""
    return {k: ("" if v is None else v) for k, v in metadata.items()}


def index_to_vectorstore(chunks: list[dict], batch_size: int = 100) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        return
    collection = get_collection()
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[_sanitize_metadata_for_chroma(chunk["metadata"]) for chunk in batch],
        )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    print(f"Loaded {len(documents)} documents")
    chunks = chunk_documents(documents)
    print(f"Created {len(chunks)} chunks")
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks to ChromaDB at {CHROMA_DIR}")


if __name__ == "__main__":
    run_pipeline()
