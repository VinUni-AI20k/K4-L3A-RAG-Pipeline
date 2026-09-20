"""Streamlit demo for the Vietnam heritage and travel RAG assistant."""

from __future__ import annotations

import html
import os
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
CHROMA_DIR = ROOT_DIR / "chroma_db"

load_dotenv(ROOT_DIR / ".env")

# Once an index exists, the embedding model must already be cached locally.
# Offline mode avoids slow Hugging Face metadata retries during a live demo.
if CHROMA_DIR.is_dir():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from src.task10_generation import generate_with_citation, reorder_for_llm

st.set_page_config(
    page_title="Viet Heritage AI",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)


CUSTOM_CSS = """
<style>
    :root {
        --ink: #172925;
        --muted: #60736d;
        --cream: #f7f4ec;
        --paper: rgba(255, 255, 255, 0.88);
        --jade: #176b5b;
        --jade-dark: #0d4d42;
        --gold: #d49a42;
        --line: rgba(23, 107, 91, 0.14);
    }

    .stApp {
        background:
            radial-gradient(circle at 82% 4%, rgba(212, 154, 66, 0.13), transparent 26rem),
            radial-gradient(circle at 8% 22%, rgba(23, 107, 91, 0.09), transparent 25rem),
            var(--cream);
        color: var(--ink);
    }

    [data-testid="stHeader"] { background: transparent; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #102f2a 0%, #0b211d 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    [data-testid="stSidebar"] * { color: #f8f4e9; }
    [data-testid="stSidebar"] [data-baseweb="slider"] * { color: #ffffff; }

    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        border: 1px solid rgba(255, 255, 255, 0.22);
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        border-color: #e2b86f;
        background: rgba(226, 184, 111, 0.14);
    }

    .block-container {
        max-width: 1120px;
        padding-top: 2.25rem;
        padding-bottom: 6rem;
    }

    .hero {
        position: relative;
        overflow: hidden;
        padding: 2.25rem 2.5rem;
        border: 1px solid var(--line);
        border-radius: 26px;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(246, 241, 226, 0.88));
        box-shadow: 0 22px 60px rgba(31, 62, 54, 0.09);
        margin-bottom: 1.3rem;
    }

    .hero::after {
        content: "";
        position: absolute;
        width: 250px;
        height: 250px;
        right: -90px;
        top: -105px;
        border-radius: 50%;
        border: 44px solid rgba(212, 154, 66, 0.12);
    }

    .eyebrow {
        color: var(--jade);
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        margin-bottom: 0.65rem;
    }

    .hero h1 {
        color: var(--ink);
        font-size: clamp(2.1rem, 5vw, 3.45rem);
        line-height: 1.03;
        letter-spacing: -0.045em;
        max-width: 720px;
        margin: 0;
    }

    .hero p {
        color: var(--muted);
        font-size: 1.02rem;
        line-height: 1.65;
        max-width: 760px;
        margin: 1rem 0 0;
    }

    .brand-mark {
        display: inline-flex;
        width: 44px;
        height: 44px;
        align-items: center;
        justify-content: center;
        border-radius: 14px;
        background: linear-gradient(145deg, #d5a450, #f0cf8a);
        color: #102f2a !important;
        font-size: 1.4rem;
        margin-bottom: 0.85rem;
    }

    .sidebar-title {
        font-size: 1.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.25rem;
    }

    .sidebar-copy {
        color: rgba(248, 244, 233, 0.70) !important;
        font-size: 0.86rem;
        line-height: 1.55;
        margin-bottom: 1.3rem;
    }

    .status-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        padding: 0.72rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.10);
        font-size: 0.84rem;
    }

    .status-value {
        color: #f2cf8e !important;
        font-weight: 700;
        text-align: right;
    }

    .metric-card {
        min-height: 106px;
        padding: 1.15rem 1.25rem;
        border: 1px solid var(--line);
        border-radius: 19px;
        background: var(--paper);
        box-shadow: 0 10px 28px rgba(31, 62, 54, 0.05);
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.09em;
        text-transform: uppercase;
    }

    .metric-value {
        color: var(--ink);
        font-size: 1.35rem;
        font-weight: 800;
        margin-top: 0.38rem;
    }

    .section-label {
        color: var(--ink);
        font-size: 0.98rem;
        font-weight: 800;
        margin: 1.4rem 0 0.65rem;
    }

    div[data-testid="stChatMessage"] {
        border: 1px solid var(--line);
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.74);
        box-shadow: 0 8px 24px rgba(31, 62, 54, 0.045);
        padding: 0.35rem 0.45rem;
        margin-bottom: 0.75rem;
    }

    div[data-testid="stChatMessage"] p { line-height: 1.68; }

    .answer-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin: 0.75rem 0 0.2rem;
    }

    .meta-chip {
        display: inline-flex;
        align-items: center;
        padding: 0.28rem 0.62rem;
        border-radius: 999px;
        background: rgba(23, 107, 91, 0.09);
        color: var(--jade-dark);
        font-size: 0.75rem;
        font-weight: 700;
    }

    .source-card {
        padding: 0.9rem 1rem;
        border-left: 3px solid var(--gold);
        border-radius: 5px 14px 14px 5px;
        background: rgba(255, 255, 255, 0.70);
        margin: 0.55rem 0;
    }

    .source-title {
        color: var(--ink);
        font-weight: 800;
        line-height: 1.35;
    }

    .source-meta {
        color: var(--muted);
        font-size: 0.79rem;
        margin-top: 0.3rem;
    }

    .empty-note {
        padding: 1rem 1.15rem;
        border: 1px dashed rgba(23, 107, 91, 0.28);
        border-radius: 16px;
        color: var(--muted);
        background: rgba(255, 255, 255, 0.45);
        font-size: 0.9rem;
    }

    .footer-note {
        color: #75857f;
        text-align: center;
        font-size: 0.76rem;
        margin-top: 2.5rem;
    }

    .stButton > button {
        border-radius: 13px;
        border-color: rgba(23, 107, 91, 0.20);
        min-height: 3rem;
        white-space: normal;
    }

    .stButton > button:hover {
        border-color: var(--jade);
        color: var(--jade-dark);
    }

    [data-testid="stChatInput"] {
        border-color: rgba(23, 107, 91, 0.25);
        box-shadow: 0 12px 34px rgba(31, 62, 54, 0.10);
    }

    @media (max-width: 700px) {
        .block-container { padding-top: 1rem; }
        .hero { padding: 1.55rem 1.35rem; border-radius: 20px; }
        .hero h1 { font-size: 2.05rem; }
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data(ttl=20, show_spinner=False)
def get_index_status() -> tuple[int, str]:
    """Return the indexed chunk count without creating an empty database."""

    if not CHROMA_DIR.is_dir():
        return 0, "Chưa tạo index"

    try:
        from src.task4_chunking_indexing import get_collection

        count = int(get_collection().count())
        return count, "Sẵn sàng" if count else "Index rỗng"
    except Exception:
        return 0, "Cần kiểm tra"


def retrieval_label(method: str) -> str:
    labels = {
        "hybrid": "Hybrid · Dense + BM25 + RRF",
        "pageindex": "PageIndex fallback",
        "dense": "Dense retrieval",
        "bm25": "BM25 retrieval",
        "none": "Không có ngữ cảnh",
    }
    return labels.get(method, method or "Không xác định")


def source_url(metadata: dict) -> str | None:
    url = metadata.get("url")
    if isinstance(url, str) and url.startswith(("https://", "http://")):
        return url

    source = metadata.get("source")
    if isinstance(source, str) and source.startswith(("https://", "http://")):
        return source

    return None


def render_sources(sources: list[dict], show_context: bool) -> None:
    """Render cited SearchResults without assuming optional metadata exists."""

    if not sources:
        st.markdown(
            '<div class="empty-note">Không có nguồn đủ tin cậy để hiển thị.</div>',
            unsafe_allow_html=True,
        )
        return

    with st.expander(f"Xem {len(sources)} nguồn đã sử dụng", expanded=False):
        for index, item in enumerate(sources, start=1):
            metadata = item.get("metadata") or {}
            title = str(metadata.get("title") or metadata.get("source") or "Nguồn không tên")
            source = str(metadata.get("source") or "Không rõ nguồn")
            doc_type = "Văn bản pháp lý" if metadata.get("doc_type") == "legal" else "Cẩm nang du lịch"
            method = str(item.get("retrieval_method") or "unknown")
            score = item.get("score")
            score_text = f"{float(score):.4f}" if isinstance(score, (int, float)) else "N/A"
            title_safe = html.escape(title)
            source_safe = html.escape(source)

            st.markdown(
                f"""
                <div class="source-card">
                    <div class="source-title">[Document {index}] {title_safe}</div>
                    <div class="source-meta">
                        {html.escape(doc_type)} &nbsp;·&nbsp;
                        {html.escape(method.upper())} &nbsp;·&nbsp;
                        score {score_text}<br>
                        {source_safe}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            url = source_url(metadata)
            if url:
                st.markdown(f"[Mở nguồn gốc ↗]({url})")

            if show_context:
                content = str(item.get("content") or "").strip()
                if content:
                    preview = content if len(content) <= 900 else f"{content[:900].rstrip()}…"
                    st.code(preview, language=None)


def render_assistant_message(message: dict, show_context: bool) -> None:
    st.markdown(message.get("content", ""))

    sources = message.get("sources") or []
    # Task 10 numbers citations after reordering context. Use the same order in
    # the UI so [Document N] always points to the matching source card.
    display_sources = reorder_for_llm(list(sources))
    retrieval_source = str(message.get("retrieval_source") or "none")
    elapsed = message.get("elapsed")
    elapsed_text = f"{float(elapsed):.2f}s" if isinstance(elapsed, (int, float)) else "--"

    st.markdown(
        f"""
        <div class="answer-meta">
            <span class="meta-chip">🔎 {html.escape(retrieval_label(retrieval_source))}</span>
            <span class="meta-chip">📚 {len(sources)} nguồn</span>
            <span class="meta-chip">⏱ {elapsed_text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_sources(display_sources, show_context)


def normalise_generation_result(result: object) -> dict:
    """Defensively normalise backend output before storing it in UI state."""

    if not isinstance(result, dict):
        raise ValueError("Generation pipeline returned an invalid result")

    answer = result.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Generation pipeline returned an empty answer")

    sources = result.get("sources")
    if not isinstance(sources, list):
        sources = []

    return {
        "answer": answer.strip(),
        "sources": sources,
        "retrieval_source": str(result.get("retrieval_source") or "none"),
    }


if "messages" not in st.session_state:
    st.session_state.messages = []


chunk_count, index_state = get_index_status()
provider = os.getenv("LLM_PROVIDER", "openai").strip().lower() or "openai"
model = os.getenv("LLM_MODEL", "").strip() or "Chưa cấu hình"

with st.sidebar:
    st.markdown('<div class="brand-mark">◈</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">Viet Heritage AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sidebar-copy">Trợ lý tra cứu du lịch và di sản Việt Nam, '
        'trả lời từ bộ tài liệu đã kiểm chứng.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("#### Trạng thái hệ thống")
    st.markdown(
        f"""
        <div class="status-row"><span>Vector index</span><span class="status-value">{html.escape(index_state)}</span></div>
        <div class="status-row"><span>Indexed chunks</span><span class="status-value">{chunk_count}</span></div>
        <div class="status-row"><span>LLM provider</span><span class="status-value">{html.escape(provider.upper())}</span></div>
        <div class="status-row"><span>Model</span><span class="status-value">{html.escape(model)}</span></div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Thiết lập truy xuất")
    top_k = st.slider(
        "Số đoạn ngữ cảnh",
        min_value=3,
        max_value=10,
        value=5,
        help="Số chunks tối đa được đưa vào context.",
    )
    show_context = st.checkbox(
        "Hiển thị nội dung chunks",
        value=False,
        help="Bật khi demo để đối chiếu câu trả lời với evidence.",
    )

    st.markdown("#### Phạm vi dữ liệu")
    st.caption("🏛️ 3 văn bản về di sản văn hóa")
    st.caption("🗺️ 5 cẩm nang điểm đến Việt Nam")
    st.caption("🧩 Hybrid retrieval: Dense + BM25 + RRF")

    st.markdown("")
    if st.button("Xóa cuộc trò chuyện", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.markdown(
    """
    <section class="hero">
        <div class="eyebrow">Vietnam Heritage Intelligence</div>
        <h1>Khám phá Việt Nam<br>từ nguồn tin cậy.</h1>
        <p>Hỏi về điểm đến, trải nghiệm du lịch và các quy định bảo tồn di sản.
        Mọi câu trả lời đều được truy xuất từ kho dữ liệu của nhóm và kèm nguồn đối chiếu.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

metric_columns = st.columns(3)
metrics = (
    ("Kho tri thức", "8 tài liệu"),
    ("Công nghệ", "Hybrid RAG"),
    ("Nguyên tắc", "Grounded answers"),
)
for column, (label, value) in zip(metric_columns, metrics):
    with column:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

selected_prompt: str | None = None
if not st.session_state.messages:
    st.markdown('<div class="section-label">Thử một câu hỏi mẫu</div>', unsafe_allow_html=True)
    examples = (
        "Hà Nội có những điểm tham quan nào nổi bật?",
        "Một ngày ở Phú Quốc nên trải nghiệm những gì?",
        "Thông tư 10/2026/TT-BVHTTDL quy định về nội dung gì?",
        "Ở Hội An có những trải nghiệm nào đáng thử?",
    )
    example_columns = st.columns(2)
    for index, prompt in enumerate(examples):
        with example_columns[index % 2]:
            if st.button(prompt, key=f"example_{index}", use_container_width=True):
                selected_prompt = prompt

if st.session_state.messages:
    st.markdown('<div class="section-label">Cuộc trò chuyện</div>', unsafe_allow_html=True)

for message in st.session_state.messages:
    avatar = "🧭" if message.get("role") == "assistant" else "👤"
    with st.chat_message(message.get("role", "assistant"), avatar=avatar):
        if message.get("role") == "assistant":
            render_assistant_message(message, show_context)
        else:
            st.markdown(message.get("content", ""))

typed_query = st.chat_input("Hỏi về du lịch, di sản hoặc văn bản pháp lý…")
query = typed_query or selected_prompt

if query:
    user_message = {"role": "user", "content": query}
    st.session_state.messages.append(user_message)

    with st.chat_message("user", avatar="👤"):
        st.markdown(query)

    with st.chat_message("assistant", avatar="🧭"):
        started_at = time.perf_counter()
        try:
            with st.spinner("Đang tìm kiếm và đối chiếu nguồn…"):
                result = normalise_generation_result(
                    generate_with_citation(query, top_k=top_k)
                )
            elapsed = time.perf_counter() - started_at
            assistant_message = {
                "role": "assistant",
                "content": result["answer"],
                "sources": result["sources"],
                "retrieval_source": result["retrieval_source"],
                "elapsed": elapsed,
            }
        except Exception:
            elapsed = time.perf_counter() - started_at
            assistant_message = {
                "role": "assistant",
                "content": (
                    "Hệ thống chưa thể truy xuất kho dữ liệu. "
                    "Vui lòng kiểm tra vector index và cấu hình model trước khi demo."
                ),
                "sources": [],
                "retrieval_source": "none",
                "elapsed": elapsed,
            }

        render_assistant_message(assistant_message, show_context)
        st.session_state.messages.append(assistant_message)

st.markdown(
    '<div class="footer-note">Câu trả lời được tạo từ kho dữ liệu của nhóm. '
    'Hãy kiểm tra nguồn trích dẫn trước khi sử dụng.</div>',
    unsafe_allow_html=True,
)
