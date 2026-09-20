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

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = 1024

COLLECTION_NAME = "rag_documents"

_MODEL = None
_GENAI_CLIENT = None
_OPENAI_CLIENT = None


def embed_texts(texts: list[str]) -> list[list[float]]:
    # TODO: Dispatch theo EMBEDDING_PROVIDER trong .env.
    #
    # Provider local gợi ý:
    # from sentence_transformers import SentenceTransformer
    # model = SentenceTransformer(EMBEDDING_MODEL)
    # return model.encode(texts).tolist()
    global _GENAI_CLIENT, _OPENAI_CLIENT, _MODEL
    if EMBEDDING_PROVIDER == "gemini":
        if _GENAI_CLIENT is None:
            from google import genai
            _GENAI_CLIENT = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
        client = _GENAI_CLIENT
        model = EMBEDDING_MODEL if EMBEDDING_MODEL and "gemini" in EMBEDDING_MODEL else "gemini-embedding-001"
        # Batch into chunks of 50 to respect API limits if needed
        all_vectors = []
        batch_size = 40
        import time
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            res = client.models.embed_content(model=model, contents=batch)
            all_vectors.extend([e.values for e in res.embeddings])
            if i + batch_size < len(texts):
                time.sleep(25)
        return all_vectors
    elif EMBEDDING_PROVIDER == "openai":
        if _OPENAI_CLIENT is None:
            from openai import OpenAI
            _OPENAI_CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        client = _OPENAI_CLIENT
        model = EMBEDDING_MODEL if EMBEDDING_MODEL and "text-embedding" in EMBEDDING_MODEL else "text-embedding-3-small"
        res = client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in res.data]
    else:
        if _MODEL is None:
            from sentence_transformers import SentenceTransformer
            _MODEL = SentenceTransformer(EMBEDDING_MODEL)
        return _MODEL.encode(texts).tolist()


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    # TODO: Tạo hoặc mở persistent collection.
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
    documents = []
    for path in STANDARDIZED_DIR.rglob("*.md"):
        if path.name.startswith("."):
            continue
        doc_type = "legal" if "legal" in path.parts else "news"
        documents.append({
            "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
            "content": path.read_text(encoding="utf-8"),
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
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for document in documents:
        for index, text in enumerate(splitter.split_text(document["content"])):
            chunks.append({
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index},
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    # TODO: Embed theo batch và giữ nguyên các field của chunk.
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    # TODO: Upsert ids, documents, embeddings và metadatas.
    collection = get_collection()
    clean_metadatas = []
    for c in chunks:
        m = dict(c["metadata"])
        if m.get("url") is None:
            m["url"] = ""
        clean_metadatas.append(m)

    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["content"] for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        metadatas=clean_metadatas,
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