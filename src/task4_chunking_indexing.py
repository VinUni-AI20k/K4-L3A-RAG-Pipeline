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
import re
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = 1024

COLLECTION_NAME = "rag_documents"

_MODEL_CACHE: Any = None


def get_embedding_model():
    """Lazy load SentenceTransformer embedding model."""
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        from sentence_transformers import SentenceTransformer
        _MODEL_CACHE = SentenceTransformer(EMBEDDING_MODEL)
    return _MODEL_CACHE


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Dispatch embedding theo cấu hình, mặc định sentence_transformers."""
    if not texts:
        return []
    
    # Check if custom provider configured
    if EMBEDDING_PROVIDER == "sentence_transformers":
        model = get_embedding_model()
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.tolist()
    
    # Fallback to SentenceTransformer
    model = get_embedding_model()
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=False).tolist()


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
    documents = []
    if not STANDARDIZED_DIR.exists():
        return documents

    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        if path.name.startswith("."):
            continue
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            continue

        doc_type = "legal" if "legal" in path.parts else "news"
        title = path.stem.replace("_", " ").title()

        # Extract url from header if present
        url = None
        match = re.search(r"\*\*Source:\*\*\s*(https?://[^\s\n]+)", content)
        if match:
            url = match.group(1).strip()

        documents.append({
            "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
            "content": content,
            "metadata": {
                "source": path.name,
                "title": title,
                "doc_type": doc_type,
                "url": url,
            },
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        split_fn = splitter.split_text
    except ImportError:
        def split_fn(text: str) -> list[str]:
            res = []
            step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
            for i in range(0, len(text), step):
                chunk = text[i : i + CHUNK_SIZE]
                if chunk.strip():
                    res.append(chunk)
            return res

    chunks = []
    for document in documents:
        doc_id = document["id"]
        doc_metadata = document["metadata"]
        text_splits = split_fn(document["content"])

        for index, text in enumerate(text_splits):
            if not text.strip():
                continue
            chunk_metadata = dict(doc_metadata)
            chunk_metadata["chunk_index"] = index
            chunks.append({
                "id": f"{doc_id}::chunk-{index}",
                "content": text,
                "metadata": chunk_metadata,
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    if not chunks:
        return chunks
    texts = [chunk["content"] for chunk in chunks]
    vectors = embed_texts(texts)
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        return
    collection = get_collection()
    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["content"] for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        metadatas=[chunk["metadata"] for chunk in chunks],
    )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    
    # Cập nhật CORPUS cho task6_lexical_search
    try:
        from . import task6_lexical_search
        task6_lexical_search.CORPUS = [
            {
                "id": chunk["id"],
                "content": chunk["content"],
                "metadata": chunk["metadata"],
            }
            for chunk in chunks
        ]
    except Exception:
        pass
        
    print(f"Indexed {len(embedded_chunks)} chunks into ChromaDB")


if __name__ == "__main__":
    run_pipeline()
