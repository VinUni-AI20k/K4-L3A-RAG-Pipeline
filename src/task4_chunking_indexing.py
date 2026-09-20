"""Load citation-ready records, chunk, embed with Gemini and upsert Chroma."""
import json, os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
CHUNK_SIZE, CHUNK_OVERLAP, CHUNKING_METHOD = 500, 50, "structure-aware"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIM, COLLECTION_NAME = 3072, "rag_documents"

def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts: return []
    if os.getenv("EMBEDDING_PROVIDER", "gemini").lower() != "gemini": raise ValueError("Only Gemini embeddings are supported")
    from google import genai
    from google.genai import types
    key = os.getenv("GEMINI_API_KEY")
    if not key: raise RuntimeError("GEMINI_API_KEY is required")
    response = genai.Client(api_key=key).models.embed_content(model=EMBEDDING_MODEL, contents=texts, config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"))
    return [item.values for item in response.embeddings]

def get_collection():
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR)).get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space":"cosine"})

def load_documents() -> list[dict]:
    documents=[]; legal_dir=STANDARDIZED_DIR/"legal"; news_dir=STANDARDIZED_DIR/"news"
    legal_files=list(legal_dir.glob("*.jsonl")); news_files=list(news_dir.glob("*.json"))
    for path in sorted(legal_files):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            x=json.loads(line); m={"source":x.get("issuer") or x.get("document_title") or x["source_id"],"title":x.get("document_title") or x["source_id"],"doc_type":"legal","url":x.get("source_url"),"source_id":x["source_id"],"document_number":x.get("document_number"),"issued_date":x.get("issued_date"),"effective_date":x.get("effective_date"),"page_start":x["page_start"],"page_end":x["page_end"],"chapter_number":x.get("chapter_number"),"section_number":x.get("section_number"),"article_number":x.get("article_number"),"clause_number":x.get("clause_number"),"point_number":x.get("point_number"),"legal_path":x.get("legal_path", ""),"trust_level":"official","structured_record_id":x["id"],"file_name":x.get("file_name"),"file_sha256":x.get("file_sha256")}
            documents.append({"id":x["id"],"content":x["normalized_text"],"metadata":m})
    for path in sorted(news_files):
        x=json.loads(path.read_text(encoding="utf-8")); m={"source":x.get("publisher") or x["source_id"],"title":x["title"],"doc_type":"news","url":x.get("canonical_url") or x.get("url"),"source_id":x["source_id"],"publisher":x.get("publisher"),"published_date":x.get("published_date"),"source_type":x.get("source_type"),"trust_level":x.get("trust_level"),"content_sha256":x.get("content_sha256")}
        documents.append({"id":x["source_id"],"content":x["content"],"metadata":m})
    canonical={p.stem for p in legal_files+news_files}
    for path in STANDARDIZED_DIR.rglob("*.md"):
        if path.stem in canonical: continue
        kind="legal" if "legal" in path.parts else "news"; documents.append({"id":path.relative_to(STANDARDIZED_DIR).as_posix(),"content":path.read_text(encoding="utf-8"),"metadata":{"source":path.name,"title":path.stem,"doc_type":kind,"url":None}})
    return documents

def chunk_documents(documents: list[dict]) -> list[dict]:
    chunks=[]
    for doc in documents:
        content=doc["content"]
        if doc["metadata"].get("doc_type")=="legal" and len(content)<=CHUNK_SIZE: texts=[content]
        else:
            texts=[]; start=0
            while start<len(content):
                end=min(start+CHUNK_SIZE,len(content)); cut=end
                if end<len(content):
                    candidates=[content.rfind(sep,start,end) for sep in ("\n\n","\n",". "," ")]; best=max(candidates)
                    if best>start+CHUNK_SIZE//2: cut=best+1
                text=content[start:cut].strip()
                if text:texts.append(text)
                if cut>=len(content):break
                start=max(cut-CHUNK_OVERLAP,start+1)
        for i,text in enumerate(texts): chunks.append({"id":f"{doc['id']}::chunk{i}","content":text,"metadata":{**doc["metadata"],"chunk_index":i}})
    return chunks

def embed_chunks(chunks:list[dict])->list[dict]:
    vectors=embed_texts([x["content"] for x in chunks])
    if len(vectors)!=len(chunks): raise ValueError("Embedding count mismatch")
    return [{**x,"embedding":v} for x,v in zip(chunks,vectors)]

def index_to_vectorstore(chunks:list[dict])->None:
    if not chunks:return
    get_collection().upsert(ids=[x["id"] for x in chunks],documents=[x["content"] for x in chunks],embeddings=[x["embedding"] for x in chunks],metadatas=[{k:v for k,v in x["metadata"].items() if v is not None} for x in chunks])

def run_pipeline():
    chunks=embed_chunks(chunk_documents(load_documents()));index_to_vectorstore(chunks);print(f"Indexed {len(chunks)} chunks")
if __name__=="__main__":run_pipeline()
