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

from dotenv import load_dotenv

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Tham số chunking
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
COLLECTION_NAME = "rag_documents"

_embedding_fn = None


def get_embedding_function():
    """Khởi tạo và cache embedding function duy nhất cho toàn bộ hệ thống."""
    global _embedding_fn
    if _embedding_fn is not None:
        return _embedding_fn

    provider = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")

    if provider == "sentence_transformers":
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(EMBEDDING_MODEL)
        _embedding_fn = lambda texts: model.encode(texts).tolist()
        return _embedding_fn

    # Fallback dùng ONNX all-MiniLM-L6-v2 mặc định của ChromaDB
    from chromadb.utils import embedding_functions

    fn = embedding_functions.DefaultEmbeddingFunction()
    _embedding_fn = lambda texts: fn(texts)
    return _embedding_fn


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Hàm embedding duy nhất — Task 4 và Task 5 bắt buộc dùng chung."""
    if not texts:
        return []
    fn = get_embedding_function()
    return fn(texts)


def get_collection():
    """Mở hoặc tạo persistent Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_documents() -> list[dict]:
    """Đọc Markdown trong data/standardized/ và trả về danh sách Document theo contract."""
    documents = []
    if not STANDARDIZED_DIR.exists():
        return documents

    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        if path.name.startswith("."):
            continue
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue

        doc_type = "legal" if "legal" in path.parts else "news"
        title = path.stem
        url = None

        # Trích xuất title và url từ header nếu có
        for line in content.splitlines()[:10]:
            if line.startswith("# "):
                title = line[2:].strip()
            elif "**Source:**" in line:
                raw_src = line.split("**Source:**", 1)[1].strip()
                if raw_src.startswith("http://") or raw_src.startswith("https://"):
                    url = raw_src

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
    """Chia Document thành chunks có id và chunk_index theo chuẩn Recursive splitter."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for document in documents:
        split_texts = splitter.split_text(document["content"])
        for index, text in enumerate(split_texts):
            chunks.append({
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {
                    **document["metadata"],
                    "chunk_index": index,
                },
            })
    return chunks


def embed_chunks(chunks: list[dict], batch_size: int = 64) -> list[dict]:
    """Thêm embedding vector vào từng chunk (chạy theo batch)."""
    if not chunks:
        return []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [chunk["content"] for chunk in batch]
        vectors = embed_texts(texts)
        for chunk, vector in zip(batch, vectors):
            chunk["embedding"] = vector
    return chunks


def index_to_vectorstore(chunks: list[dict], batch_size: int = 500) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        return
    collection = get_collection()

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        metadatas = []
        for chunk in batch:
            metadata = dict(chunk["metadata"])
            if metadata.get("url") is None:
                metadata["url"] = ""
            metadatas.append(metadata)

        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=metadatas,
        )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    print("Loading documents from standardized directory...")
    documents = load_documents()
    print(f"Loaded {len(documents)} documents.")

    print(f"Chunking documents (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    chunks = chunk_documents(documents)
    print(f"Generated {len(chunks)} chunks.")

    print("Embedding chunks with shared embedding model...")
    embedded_chunks = embed_chunks(chunks)

    print("Indexing into ChromaDB (cosine distance)...")
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks")


if __name__ == "__main__":
    run_pipeline()
