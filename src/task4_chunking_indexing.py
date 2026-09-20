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


STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

COLLECTION_NAME = "rag_documents"

# Ngưỡng cứng cho độ dài 1 chunk (ký tự). RecursiveCharacterTextSplitter thường
# tôn trọng CHUNK_SIZE nhưng không đảm bảo tuyệt đối khi không tìm được
# separator phù hợp (vd. một đoạn liền không xuống dòng, không dấu chấm) — khi
# đó phải cắt cứng để không vi phạm hợp đồng chunk.
_HARD_MAX_CHUNK_CHARS = int(CHUNK_SIZE * 1.1)

# Tên văn bản đầy đủ, trích từ chính nội dung file (không bịa), dùng làm title
# hiển thị khi trích dẫn nguồn ở Task 10 thay vì path.stem (vd. "luat-nha-o").
# Nguồn trích:
#   - luat-nha-o.md: "LUẬT / NHÀ Ở" + "Luật số: 27/2023/QH15" (đầu file).
#   - luat-kinh-doanh-bds.md: "LUẬT / KINH DOANH BẤT ĐỘNG SẢN" + "Luật số: 29/2023/QH15".
#   - luat_bao_ve_nguoi_tieu_dung_2023.md: "LUẬT / BẢO VỆ QUYỀN LỢI NGƯỜI TIÊU DÙNG"
#     + "Luật số: 19/2023/QH15".
#   - mau-so-1a.md: "Mẫu số Ia: nội dung hợp đồng mẫu áp dụng trong mua bán căn hộ chung cư".
DOCUMENT_TITLES: dict[str, str] = {
    "luat-nha-o.md": "Luật Nhà ở (Luật số 27/2023/QH15)",
    "luat-kinh-doanh-bds.md": "Luật Kinh doanh bất động sản (Luật số 29/2023/QH15)",
    "luat_bao_ve_nguoi_tieu_dung_2023.md": (
        "Luật Bảo vệ quyền lợi người tiêu dùng (Luật số 19/2023/QH15)"
    ),
    "mau-so-1a.md": (
        "Mẫu số Ia: Nội dung hợp đồng mẫu áp dụng trong mua bán căn hộ chung cư"
    ),
}

# URL nguồn chính thức (vd. congbao.chinhphu.vn, datafiles.chinhphu.vn) — để trống
# (None) nếu không tìm được URL đã xác minh, KHÔNG bịa. Nhóm điền sau khi có nguồn
# đã xác minh để citation ở Task 10 dẫn ngược được về văn bản gốc.
# Xác minh: kiểm curl -sIL content-length khớp byte của file local.
DOCUMENT_URLS: dict[str, str | None] = {
    "luat-nha-o.md": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/01/luat27.pdf",
    "luat-kinh-doanh-bds.md": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/01/luat29.pdf",
    "luat_bao_ve_nguoi_tieu_dung_2023.md": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2023/7/luat19_2023.pdf",
    "mau-so-1a.md": None,
}

# Cache model embedding local ở cấp module (lazy) — bge-m3 nặng ~2+ GB, không
# được load lại mỗi lần gọi embed_texts().
_sentence_transformer_model = None


def _resolve_title(path: Path, content: str) -> str:
    """Suy ra title hiển thị cho document.

    Ưu tiên: DOCUMENT_TITLES (tên văn bản thật) -> heading '#' đầu tiên trong
    nội dung -> path.stem (fallback cuối cùng, chỉ dùng khi không có gì khác).
    """
    if path.name in DOCUMENT_TITLES:
        return DOCUMENT_TITLES[path.name]
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                return heading
    return path.stem


def load_documents() -> list[dict]:
    """Đọc mọi Markdown trong STANDARDIZED_DIR và trả về danh sách Document.

    Không crash khi thư mục không tồn tại hoặc rỗng (vd. news/ đang tạm hoãn) —
    chỉ in cảnh báo rồi trả list (có thể rỗng), để pipeline vẫn chạy được trên
    corpus chỉ-có-legal.
    """
    if not STANDARDIZED_DIR.is_dir():
        print(f"[task4] Cảnh báo: không tìm thấy thư mục {STANDARDIZED_DIR}, bỏ qua.")
        return []

    paths = sorted(
        path
        for path in STANDARDIZED_DIR.rglob("*.md")
        if path.is_file() and not path.name.startswith(".")
    )
    if not paths:
        print(f"[task4] Cảnh báo: thư mục {STANDARDIZED_DIR} không có file .md nào.")
        return []

    documents: list[dict] = []
    for path in paths:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            print(f"[task4] Cảnh báo: '{path.name}' rỗng, bỏ qua không đưa vào corpus.")
            continue

        doc_type = "legal" if "legal" in path.parts else "news"
        documents.append(
            {
                "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
                "content": content,
                "metadata": {
                    "source": path.name,
                    "title": _resolve_title(path, content),
                    "doc_type": doc_type,
                    "url": DOCUMENT_URLS.get(path.name),
                },
            }
        )

    print(f"[task4] Đã load {len(documents)} document từ {STANDARDIZED_DIR}.")
    return documents


def _split_oversized(text: str) -> list[str]:
    """Cắt cứng một đoạn dài hơn ngưỡng thành nhiều phần <= CHUNK_SIZE.

    RecursiveCharacterTextSplitter không đảm bảo tuyệt đối mọi đoạn <=
    chunk_size (khi không tìm được separator phù hợp trong đoạn), nên đây là
    lưới an toàn cuối cùng để không vi phạm hợp đồng "chunk <= 1.1 * CHUNK_SIZE".
    """
    return [
        text[start : start + CHUNK_SIZE]
        for start in range(0, len(text), CHUNK_SIZE)
        if text[start : start + CHUNK_SIZE].strip()
    ]


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index.

    chunk_index được đánh số lại từ 0 CHO TỪNG DOCUMENT (đúng ngữ nghĩa "thứ tự
    chunk trong document" theo contract), không phải theo vị trí trong list
    tổng trả về. Với input chỉ 1 document (như test contract), hai cách đánh
    số trùng nhau nên vẫn pass test.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[dict] = []
    for document in documents:
        raw_pieces = splitter.split_text(document["content"])

        # Lưới an toàn: không tin tưởng tuyệt đối splitter tôn trọng chunk_size.
        safe_pieces: list[str] = []
        for piece in raw_pieces:
            if len(piece) <= _HARD_MAX_CHUNK_CHARS:
                safe_pieces.append(piece)
            else:
                safe_pieces.extend(_split_oversized(piece))

        index = 0
        for text in safe_pieces:
            if not text.strip():
                continue
            chunks.append(
                {
                    "id": f"{document['id']}::chunk-{index}",
                    "content": text,
                    # Copy metadata (không share reference) để tránh mutate chéo
                    # giữa các chunk của cùng document.
                    "metadata": {**document["metadata"], "chunk_index": index},
                }
            )
            index += 1

    print(f"[task4] Đã chia {len(documents)} document thành {len(chunks)} chunk.")
    return chunks


def _embed_with_sentence_transformers(texts: list[str]) -> list[list[float]]:
    global _sentence_transformer_model

    if _sentence_transformer_model is None:
        from sentence_transformers import SentenceTransformer

        print(f"[task4] Đang load embedding model '{EMBEDDING_MODEL}' (lần đầu, có thể chậm)...")
        _sentence_transformer_model = SentenceTransformer(EMBEDDING_MODEL)

    return _sentence_transformer_model.encode(texts).tolist()


def _embed_with_openai(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("EMBEDDING_PROVIDER=openai nhưng thiếu OPENAI_API_KEY trong .env")

    model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def _embed_with_gemini(texts: list[str]) -> list[list[float]]:
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("EMBEDDING_PROVIDER=gemini nhưng thiếu GEMINI_API_KEY trong .env")

    model = os.environ.get("GEMINI_EMBEDDING_MODEL", "text-embedding-004")
    client = genai.Client(api_key=api_key)
    result = client.models.embed_content(model=model, contents=texts)
    return [embedding.values for embedding in result.embeddings]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed danh sách text, dispatch provider theo EMBEDDING_PROVIDER trong .env.

    Mặc định dùng sentence_transformers (local, bge-m3). Không load model/gọi
    network khi texts rỗng.
    """
    if not texts:
        return []

    from dotenv import load_dotenv

    load_dotenv()
    provider = os.environ.get("EMBEDDING_PROVIDER", "sentence_transformers").strip().lower()

    if provider == "sentence_transformers":
        return _embed_with_sentence_transformers(texts)
    if provider == "openai":
        return _embed_with_openai(texts)
    if provider == "gemini":
        return _embed_with_gemini(texts)

    raise ValueError(f"EMBEDDING_PROVIDER không hỗ trợ: '{provider}'")


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk, giữ nguyên các field khác.

    Embed theo batch (in tiến độ) vì corpus thật có thể 1.000+ chunk và chạy
    CPU sẽ lâu. Kiểm tra dimension trả về khớp EMBEDDING_DIM — bất biến bắt
    buộc để Task 5 dùng chung model/dimension.
    """
    if not chunks:
        print("[task4] Cảnh báo: không có chunk nào để embed.")
        return chunks

    batch_size = 32
    total = len(chunks)

    for start in range(0, total, batch_size):
        batch = chunks[start : start + batch_size]
        vectors = embed_texts([chunk["content"] for chunk in batch])

        for chunk, vector in zip(batch, vectors):
            if len(vector) != EMBEDDING_DIM:
                raise ValueError(
                    f"Embedding dimension không khớp: kỳ vọng {EMBEDDING_DIM}, "
                    f"thực tế {len(vector)} (model có thể đã đổi)."
                )
            chunk["embedding"] = vector

        done = min(start + batch_size, total)
        print(f"[task4] Đã embed {done}/{total} chunk.")

    return chunks


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB theo batch.

    Dùng upsert (không phải add) để chạy lại pipeline không tạo dữ liệu trùng.
    """
    if not chunks:
        print("[task4] Cảnh báo: không có chunk nào để index.")
        return

    collection = get_collection()
    batch_size = 100
    total = len(chunks)

    for start in range(0, total, batch_size):
        batch = chunks[start : start + batch_size]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[chunk["metadata"] for chunk in batch],
        )
        done = min(start + batch_size, total)
        print(f"[task4] Đã index {done}/{total} chunk vào '{COLLECTION_NAME}'.")


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(
        f"[task4] Hoàn tất: {len(documents)} document, {len(chunks)} chunk, "
        f"{len(embedded_chunks)} chunk đã index."
    )


if __name__ == "__main__":
    run_pipeline()
