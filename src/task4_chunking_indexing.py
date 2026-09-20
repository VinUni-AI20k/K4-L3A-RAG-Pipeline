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

from pathlib import Path
import os

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 3072

COLLECTION_NAME = "rag_documents"


def _get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _metadata_for_chroma(metadata: dict) -> dict:
    return {
        key: ("" if value is None else value)
        for key, value in metadata.items()
    }


def _fallback_split_text(text: str) -> list[str]:
    chunks = []
    start = 0
    text = text.strip()
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            candidates = [
                text.rfind(separator, start, end)
                for separator in ("\n\n", "\n", ". ", " ")
            ]
            split_at = max(candidates)
            if split_at > start:
                end = split_at + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    # TODO: Dispatch theo EMBEDDING_PROVIDER trong .env.
    #
    # Provider local gợi ý:
    # from sentence_transformers import SentenceTransformer
    # model = SentenceTransformer(EMBEDDING_MODEL)
    # return model.encode(texts).tolist()
    if not texts:
        return []

    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip("\"'")

    provider = _get_env("EMBEDDING_PROVIDER", "gemini").lower()
    default_models = {
        "gemini": "gemini-embedding-001",
        "openai": "text-embedding-3-small",
    }
    model_name = (
        _get_env("EMBEDDING_MODEL")
        or default_models.get(provider)
        or "gemini-embedding-001"
    )

    if provider in {"sentence_transformers", "local"}:
        raise RuntimeError(
            "EMBEDDING_PROVIDER đang là local/sentence_transformers, "
            "sẽ tải model rất nặng. Hãy dùng openai hoặc gemini trong .env."
        )

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=_get_env("OPENAI_API_KEY") or None)
        response = client.embeddings.create(model=model_name, input=texts)
        return [item.embedding for item in response.data]

    if provider == "gemini":
        from google import genai
        import time

        client = genai.Client(api_key=_get_env("GEMINI_API_KEY") or None)
        vectors = []
        for start in range(0, len(texts), 100):
            batch = texts[start:start + 100]
            for attempt in range(3):
                try:
                    response = client.models.embed_content(
                        model=model_name,
                        contents=batch,
                    )
                    break
                except Exception as error:
                    message = str(error)
                    if "429" not in message and "RESOURCE_EXHAUSTED" not in message:
                        raise
                    if attempt == 2:
                        raise
                    time.sleep(30)
            vectors.extend(embedding.values for embedding in response.embeddings)
        return vectors

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider}")


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    # TODO: Tạo hoặc mở persistent collection.
    #
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    # TODO: Đọc mọi .md và tạo Document theo contract.
    #
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue

        relative_path = path.relative_to(STANDARDIZED_DIR)
        doc_type = "legal" if "legal" in relative_path.parts else "news"
        documents.append({
            "id": relative_path.as_posix(),
            "content": content,
            "metadata": {
                "source": path.name,
                "title": path.stem,
                "doc_type": doc_type,
                "url": None,
            },
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    # TODO: Chunk bằng RecursiveCharacterTextSplitter.
    #
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        splitter = None
    else:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    chunks = []
    for document in documents:
        if splitter is None:
            split_texts = _fallback_split_text(document["content"])
        else:
            split_texts = splitter.split_text(document["content"])
        for index, text in enumerate(text.strip() for text in split_texts):
            if not text:
                continue
            chunks.append({
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index},
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    # TODO: Embed theo batch và giữ nguyên các field của chunk.
    #
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    if len(vectors) != len(chunks):
        raise ValueError("Embedding count does not match chunk count")

    embedded_chunks = []
    for chunk, vector in zip(chunks, vectors):
        embedded_chunk = {**chunk, "embedding": vector}
        embedded_chunks.append(embedded_chunk)
    return embedded_chunks


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    # TODO: Upsert ids, documents, embeddings và metadatas.
    #
    if not chunks:
        return

    collection = get_collection()
    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["content"] for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        metadatas=[_metadata_for_chroma(chunk["metadata"]) for chunk in chunks],
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