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

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = 1024

COLLECTION_NAME = "rag_documents"

_model = None


def _get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        try:
            _model = SentenceTransformer(EMBEDDING_MODEL)
        except Exception:
            _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed danh sách văn bản thành vectors."""
    if not texts:
        return []
    provider = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").lower()
    if provider == "sentence_transformers":
        model = _get_embedding_model()
        return model.encode(texts, normalize_embeddings=True).tolist()
    elif provider == "gemini":
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            model = _get_embedding_model()
            return model.encode(texts, normalize_embeddings=True).tolist()
        client = genai.Client(api_key=api_key)
        res = client.models.embed_content(
            model="text-embedding-004",
            contents=texts,
        )
        return [e.values for e in res.embeddings]
    elif provider == "openai":
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            model = _get_embedding_model()
            return model.encode(texts, normalize_embeddings=True).tolist()
        client = OpenAI(api_key=api_key)
        resp = client.embeddings.create(input=texts, model="text-embedding-3-small")
        return [item.embedding for item in resp.data]
    else:
        model = _get_embedding_model()
        return model.encode(texts, normalize_embeddings=True).tolist()


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
        raw = path.read_text(encoding="utf-8")
        title = path.stem
        doc_type = "legal" if "legal" in path.parts else "news"
        url = None
        content = raw

        # Tách front matter nếu có
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1]
                content = parts[2].strip()
                for line in fm_text.strip().splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k == "title" and v:
                            title = v
                        elif k == "doc_type" and v:
                            doc_type = v
                        elif k in ("source_url", "url") and v:
                            url = v

        if not content:
            content = raw.strip()

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


def _split_text_recursive(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Chia văn bản đệ quy theo đoạn/câu/từ không cần nạp thư viện nặng."""
    if len(text) <= chunk_size:
        return [text]

    separators = ["\n\n", "\n", ". ", " ", ""]

    def _split(s: str, seps: list[str]) -> list[str]:
        if len(s) <= chunk_size or not seps:
            return [s]
        sep = seps[0]
        splits = s.split(sep) if sep else list(s)
        results = []
        buf = ""
        for item in splits:
            cand = (buf + sep + item) if buf else item
            if len(cand) <= chunk_size:
                buf = cand
            else:
                if buf:
                    results.append(buf)
                    overlap_buf = buf[max(0, len(buf) - chunk_overlap):]
                    buf = (overlap_buf + sep + item) if overlap_buf else item
                else:
                    sub = _split(item, seps[1:])
                    results.extend(sub[:-1])
                    buf = sub[-1]
        if buf:
            results.append(buf)
        return results

    raw_chunks = _split(text, separators)
    final_chunks = []
    for c in raw_chunks:
        cleaned = c.strip()
        if not cleaned:
            continue
        if len(cleaned) <= chunk_size:
            final_chunks.append(cleaned)
        else:
            step = max(1, chunk_size - chunk_overlap)
            for i in range(0, len(cleaned), step):
                part = cleaned[i:i + chunk_size].strip()
                if part:
                    final_chunks.append(part)
    return final_chunks or [text[:chunk_size]]


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    chunks = []
    for document in documents:
        splits = _split_text_recursive(document["content"], CHUNK_SIZE, CHUNK_OVERLAP)
        for index, text in enumerate(splits):
            cleaned = text.strip()
            if not cleaned:
                continue
            chunk_id = f"{document['id']}::chunk-{index}"
            chunk_metadata = dict(document["metadata"])
            chunk_metadata["chunk_index"] = index
            chunks.append({
                "id": chunk_id,
                "content": cleaned,
                "metadata": chunk_metadata,
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    if not chunks:
        return []
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
    batch_size = 200
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        sanitized_metadatas = []
        for c in batch:
            meta = {}
            for k, v in c["metadata"].items():
                meta[k] = "" if v is None else v
            sanitized_metadatas.append(meta)
        collection.upsert(
            ids=[c["id"] for c in batch],
            documents=[c["content"] for c in batch],
            embeddings=[c["embedding"] for c in batch],
            metadatas=sanitized_metadatas,
        )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    print(f"Loaded {len(documents)} documents")
    chunks = chunk_documents(documents)
    print(f"Created {len(chunks)} chunks")
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks to ChromaDB successfully.")


if __name__ == "__main__":
    run_pipeline()
