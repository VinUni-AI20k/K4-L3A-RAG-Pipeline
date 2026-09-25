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
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Văn bản chính sách tiếng Việt: mỗi điều khoản thường 300–900 ký tự. 800 ký tự
# giữ trọn phần lớn điều khoản trong một chunk; overlap 150 giữ ngữ cảnh khi
# một điều khoản bị cắt giữa chừng.
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
CHUNKING_METHOD = "recursive"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL") or "BAAI/bge-m3"
EMBEDDING_DIM = 1024
EMBED_BATCH_SIZE = 16

COLLECTION_NAME = "rag_documents"


@lru_cache(maxsize=1)
def _sentence_transformer():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed bằng provider trong .env; vector đã chuẩn hoá L2 cho cosine."""
    if not texts:
        return []
    texts = [unicodedata.normalize("NFC", text) for text in texts]
    if EMBEDDING_PROVIDER == "sentence_transformers":
        vectors = _sentence_transformer().encode(
            texts,
            batch_size=EMBED_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > EMBED_BATCH_SIZE,
        )
        return vectors.tolist()
    if EMBEDDING_PROVIDER == "openai":
        from openai import OpenAI

        response = OpenAI().embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in response.data]
    if EMBEDDING_PROVIDER == "gemini":
        from google import genai

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.embed_content(model=EMBEDDING_MODEL, contents=texts)
        return [list(item.values) for item in response.embeddings]
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}")


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Đọc frontmatter do Task 3 ghi (mỗi value là JSON)."""
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not match:
        return {}, text
    metadata = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(": ")
        if sep:
            try:
                metadata[key.strip()] = json.loads(value)
            except json.JSONDecodeError:
                metadata[key.strip()] = value.strip()
    return metadata, text[match.end():].strip()


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        front, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not body.strip():
            continue
        doc_type = "legal" if "legal" in path.relative_to(STANDARDIZED_DIR).parts else "news"
        metadata = {
            "source": front.get("source_file") or path.name,
            "title": front.get("title") or path.stem,
            "doc_type": doc_type,
            "url": front.get("url") or None,
        }
        for key in ("audience", "category"):
            if front.get(key):
                metadata[key] = front[key]
        documents.append({
            "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
            "content": body,
            "metadata": metadata,
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
    )
    chunks = []
    for document in documents:
        texts = [text.strip() for text in splitter.split_text(document["content"])]
        for index, text in enumerate(t for t in texts if t):
            chunks.append({
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index},
            })
    return chunks


def embedding_text(chunk: dict) -> str:
    """Gắn title tài liệu vào text khi embed để chunk ngắn vẫn mang ngữ cảnh."""
    return f"{chunk['metadata']['title']}\n\n{chunk['content']}"


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    vectors = embed_texts([embedding_text(chunk) for chunk in chunks])
    return [{**chunk, "embedding": vector} for chunk, vector in zip(chunks, vectors)]


def _chroma_metadata(metadata: dict) -> dict:
    # Chroma không lưu được giá trị None; Task 5 khôi phục url=None khi đọc.
    return {key: value for key, value in metadata.items() if value is not None}


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB và xoá chunk cũ không còn trong corpus."""
    collection = get_collection()
    new_ids = {chunk["id"] for chunk in chunks}
    stale_ids = [item_id for item_id in collection.get(include=[])["ids"] if item_id not in new_ids]
    if stale_ids:
        collection.delete(ids=stale_ids)

    batch = 256
    for start in range(0, len(chunks), batch):
        part = chunks[start:start + batch]
        collection.upsert(
            ids=[chunk["id"] for chunk in part],
            documents=[chunk["content"] for chunk in part],
            embeddings=[chunk["embedding"] for chunk in part],
            metadatas=[_chroma_metadata(chunk["metadata"]) for chunk in part],
        )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks from {len(documents)} documents")


if __name__ == "__main__":
    run_pipeline()
