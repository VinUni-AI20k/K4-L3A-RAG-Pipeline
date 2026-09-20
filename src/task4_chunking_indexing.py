"""Load, chunk, embed with Gemini, and index the corpus."""
import hashlib
import os
import re
import time
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
from .contracts import validate_document

load_dotenv()
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
CHUNK_SIZE, CHUNK_OVERLAP = 900, 120
CHUNKING_METHOD = "recursive"
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
EMBEDDING_DIM = 3072
COLLECTION_NAME = "rag_documents"

def _gemini_client():
    from google import genai
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return genai.Client(api_key=key)

def _embed_batch(client, batch: list[str], offset: int) -> list[list[float]]:
    """Embed one batch, splitting it when Gemini returns a partial response."""
    from google.genai import types

    contents = [types.Content(parts=[types.Part(text=text)]) for text in batch]
    for attempt in range(6):
        try:
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=contents,
                config={"task_type": "RETRIEVAL_DOCUMENT"},
            )
            embeddings = response.embeddings or []
            vectors = [list(item.values or []) for item in embeddings]
            if len(vectors) == len(batch) and all(vectors):
                return vectors
            break
        except Exception as exc:
            if "429" not in str(exc) or attempt == 5:
                raise
            tqdm.write(f"[Cảnh báo] Quá tải API (Lỗi 429). Đang đợi 60s để thử lại (Lần {attempt + 1}/5)...")
            time.sleep(60)

    # Some Gemini endpoints occasionally return only part of a large batch.
    # Bisecting preserves order and isolates a problematic input if one exists.
    if len(batch) > 1:
        middle = len(batch) // 2
        return (
            _embed_batch(client, batch[:middle], offset)
            + _embed_batch(client, batch[middle:], offset + middle)
        )

    digest = hashlib.sha1(batch[0].encode("utf-8")).hexdigest()[:12]
    raise RuntimeError(
        f"Gemini did not return an embedding for text #{offset} "
        f"(sha1={digest}, chars={len(batch[0])})"
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    client = _gemini_client()
    vectors: list[list[float]] = []

    for start in tqdm(range(0, len(texts), 20), desc="Embedding Chunks", unit="batch"):
        batch = texts[start:start + 20]
        vectors.extend(_embed_batch(client, batch, start))
    return vectors

def get_collection():
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

def load_documents() -> list[dict]:
    documents = []
    md_files = list(STANDARDIZED_DIR.rglob("*.md"))
    
    for path in tqdm(sorted(md_files), desc="Loading Documents", unit="file"):
        content = path.read_text(encoding="utf-8").strip()
        if not content or path.name.startswith("."):
            continue
        relative = path.relative_to(STANDARDIZED_DIR).as_posix()
        title = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        url = re.search(r"^- \*\*Source:\*\*\s*(\S+)", content, re.MULTILINE)
        item = {
            "id": relative, 
            "content": content, 
            "metadata": {
                "source": relative, 
                "title": title.group(1).strip() if title else path.stem, 
                "doc_type": "legal" if "legal" in path.parts else "news", 
                "url": url.group(1) if url else None
            }
        }
        validate_document(item)
        documents.append(item)
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""]
    )
    chunks = []
    for document in tqdm(documents, desc="Chunking Documents", unit="doc"):
        validate_document(document)
        for index, text in enumerate(splitter.split_text(document["content"])):
            text = text.strip()
            if not text:
                continue
            digest = hashlib.sha1(text.encode()).hexdigest()[:12]
            item = {
                "id": f"{document['id']}::chunk-{index}-{digest}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index}
            }
            validate_document(item, require_chunk=True)
            chunks.append(item)
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    vectors = embed_texts([item["content"] for item in chunks])
    return [{**item, "embedding": vector} for item, vector in zip(chunks, vectors)]


def index_to_vectorstore(chunks: list[dict]) -> None:
    collection = get_collection()
    stale = set(collection.get(include=[]).get("ids", [])) - {x["id"] for x in chunks}
    if stale:
        collection.delete(ids=list(stale))
        
    for start in tqdm(range(0, len(chunks), 100), desc="Upserting DB", unit="batch"):
        batch = chunks[start:start + 100]
        collection.upsert(
            ids=[x["id"] for x in batch],
            documents=[x["content"] for x in batch],
            embeddings=[x["embedding"] for x in batch],
            metadatas=[x["metadata"] for x in batch]
        )


def _same_metadata(stored: dict, current: dict) -> bool:
    """Treat Chroma's omitted nullable fields as equivalent to ``None``."""
    keys = set(stored) | set(current)
    return all(
        (stored.get(key) in (None, "") and current.get(key) in (None, ""))
        or stored.get(key) == current.get(key)
        for key in keys
    )


def run_pipeline() -> None:
    documents = load_documents()
    chunks = chunk_documents(documents)
    collection = get_collection()
    stored = collection.get(include=["metadatas"])
    existing = dict(zip(stored.get("ids", []), stored.get("metadatas", [])))
    force_reindex = os.getenv("FORCE_REINDEX", "").lower() in {"1", "true", "yes"}
    wanted_ids = {item["id"] for item in chunks}

    pending = [item for item in chunks
        if force_reindex or item["id"] not in existing
        or not _same_metadata(existing[item["id"]], item["metadata"])]
        
    if pending:
        embedded = embed_chunks(pending)
        for start in tqdm(range(0, len(embedded), 100), desc="Upserting Pending", unit="batch"):
            batch = embedded[start:start + 100]
            collection.upsert(
                ids=[item["id"] for item in batch],
                documents=[item["content"] for item in batch],
                embeddings=[item["embedding"] for item in batch],
                metadatas=[item["metadata"] for item in batch],
            )

    # Delete obsolete IDs only after every replacement embedding is safely stored.
    stale_ids = sorted(set(existing) - wanted_ids)
    if stale_ids:
        collection.delete(ids=stale_ids)

    unchanged = len(chunks) - len(pending)
    print(
        f"Corpus: {len(documents)} documents / {len(chunks)} chunks; "
        f"embedded: {len(pending)}, unchanged: {unchanged}, deleted: {len(stale_ids)}"
    )

if __name__ == "__main__":
    run_pipeline()
