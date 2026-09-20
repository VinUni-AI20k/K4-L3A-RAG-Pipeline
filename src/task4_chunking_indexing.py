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

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1536

COLLECTION_NAME = "rag_documents"

# Provider được chọn qua biến môi trường EMBEDDING_PROVIDER trong .env
# Giá trị hỗ trợ: "local" (sentence-transformers, mặc định) | "openai"
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")

_local_model = None  # cache model để không load lại mỗi lần gọi


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Dispatch embedding theo EMBEDDING_PROVIDER. Dùng chung cho Task 4 và Task 5."""
    if not texts:
        return []

    if EMBEDDING_PROVIDER == "sentence_transformers":
        return _embed_texts_local(texts)
    elif EMBEDDING_PROVIDER == "openai":
        return _embed_texts_openai(texts)
    elif EMBEDDING_PROVIDER == "gemini":
        return _embed_texts_gemini(texts)
    else:
        raise ValueError(
            f"EMBEDDING_PROVIDER không hợp lệ: '{EMBEDDING_PROVIDER}'. "
            "Chỉ hỗ trợ 'sentence_transformers', 'openai' hoặc 'gemini'."
        )


def _embed_texts_local(texts: list[str]) -> list[list[float]]:
    """Embed bằng sentence-transformers, chạy local, không cần API key."""
    global _local_model
    from sentence_transformers import SentenceTransformer

    if _local_model is None:
        _local_model = SentenceTransformer(EMBEDDING_MODEL)

    vectors = _local_model.encode(
        texts,
        batch_size=16,
        show_progress_bar=False,
        normalize_embeddings=True,  # cần cho cosine distance chính xác
    )
    return vectors.tolist()


def _embed_texts_openai(texts: list[str]) -> list[list[float]]:
    """Embed qua OpenAI-compatible API (đọc OPENAI_API_KEY từ .env)."""
    from openai import OpenAI

    client = OpenAI()
    model_name = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    response = client.embeddings.create(model=model_name, input=texts)
    return [item.embedding for item in response.data]


def _embed_texts_gemini(texts: list[str]) -> list[list[float]]:
    """Embed qua Gemini API (đọc GEMINI_API_KEY từ .env)."""
    import google.generativeai as genai

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model_name = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")

    vectors = []
    for text in texts:
        result = genai.embed_content(model=model_name, content=text)
        vectors.append(result["embedding"])
    return vectors


def get_collection():
    """Mở hoặc tạo Chroma persistent collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_documents() -> list[dict]:
    """Đọc mọi file Markdown trong data/standardized/ và trả về danh sách Document."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        doc_type = "legal" if "legal" in path.parts else "news"
        documents.append(
            {
                "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
                "content": path.read_text(encoding="utf-8"),
                "metadata": {
                    "source": path.name,
                    "title": path.stem,
                    "doc_type": doc_type,
                    "url": None,
                },
            }
        )
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia mỗi Document thành các chunk có id ổn định và chunk_index."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for document in documents:
        for index, text in enumerate(splitter.split_text(document["content"])):
            chunks.append(
                {
                    "id": f"{document['id']}::chunk-{index}",
                    "content": text,
                    "metadata": {**document["metadata"], "chunk_index": index},
                }
            )
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk, embed theo batch bằng embed_texts()."""
    BATCH_SIZE = 32
    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]
        vectors = embed_texts([chunk["content"] for chunk in batch])
        for chunk, vector in zip(batch, vectors):
            chunk["embedding"] = vector
    return chunks


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB (ids, documents, embeddings, metadatas)."""
    if not chunks:
        print("  Không có chunk nào để index.")
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
    print(f"=== Task 4: Chunking, Embedding, Indexing (provider={EMBEDDING_PROVIDER}) ===\n")

    documents = load_documents()
    print(f"[1/4] Loaded {len(documents)} documents")

    chunks = chunk_documents(documents)
    print(f"[2/4] Chunked into {len(chunks)} chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")

    embedded_chunks = embed_chunks(chunks)
    print(f"[3/4] Embedded {len(embedded_chunks)} chunks (dim={EMBEDDING_DIM})")

    index_to_vectorstore(embedded_chunks)
    print(f"[4/4] Indexed {len(embedded_chunks)} chunks into '{COLLECTION_NAME}'")


if __name__ == "__main__":
    run_pipeline()