"""Load, chunk, embed with Gemini, and index the corpus."""
import hashlib
import os
import re
import time
from pathlib import Path
from dotenv import load_dotenv
from .contracts import validate_document

load_dotenv()
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
CHUNK_SIZE, CHUNK_OVERLAP = 900, 120
CHUNKING_METHOD = "recursive"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIM = 3072
COLLECTION_NAME = "rag_documents"

def _gemini_client():
    from google import genai
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return genai.Client(api_key=key)

def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    client, vectors = _gemini_client(), []
    for start in range(0, len(texts), 80):
        batch = texts[start:start + 80]
        for attempt in range(6):
            try:
                res = client.models.embed_content(model=EMBEDDING_MODEL,
                    contents=batch, config={"task_type": "RETRIEVAL_DOCUMENT"})
                break
            except Exception as exc:
                if "429" not in str(exc) or attempt == 5:
                    raise
                time.sleep(60)
        vectors.extend(list(item.values) for item in res.embeddings)
    if len(vectors) != len(texts):
        raise RuntimeError("Embedding count mismatch")
    return vectors

def get_collection():
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"})

def load_documents() -> list[dict]:
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        if not content or path.name.startswith("."):
            continue
        relative = path.relative_to(STANDARDIZED_DIR).as_posix()
        title = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        url = re.search(r"^- \*\*Source:\*\*\s*(\S+)", content, re.MULTILINE)
        item = {"id": relative, "content": content, "metadata": {"source": relative, "title": title.group(1).strip() if title else path.stem, "doc_type": "legal" if "legal" in path.parts else "news", "url": url.group(1) if url else None}}
        validate_document(item)
        documents.append(item)
    return documents

def chunk_documents(documents: list[dict]) -> list[dict]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""])
    chunks = []
    for document in documents:
        validate_document(document)
        for index, text in enumerate(splitter.split_text(document["content"])):
            text = text.strip()
            if not text:
                continue
            digest = hashlib.sha1(text.encode()).hexdigest()[:12]
            item = {"id": f"{document['id']}::chunk-{index}-{digest}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index}}
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
    for start in range(0, len(chunks), 100):
        batch = chunks[start:start + 100]
        collection.upsert(ids=[x["id"] for x in batch],
            documents=[x["content"] for x in batch],
            embeddings=[x["embedding"] for x in batch],
            metadatas=[x["metadata"] for x in batch])

def run_pipeline() -> None:
    documents = load_documents()
    chunks = chunk_documents(documents)
    index_to_vectorstore(embed_chunks(chunks))
    print(f"Indexed {len(chunks)} chunks from {len(documents)} documents")

if __name__ == "__main__":
    run_pipeline()
