"""
Streamlit chat interface for the Vietnam Traffic Law RAG Pipeline.
Designed with a modern, glassmorphic UI, structured citation cards,
and interactive retrieval parameters.
"""

import html
import os
import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


load_dotenv()

# Cấu hình trang
st.set_page_config(
    page_title="Trợ lý Luật Giao thông AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS giao diện cao cấp
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Thiết lập bảng màu & theme */
    :root {
        --primary-gradient: linear-gradient(135deg, #059669 0%, #10b981 50%, #047857 100%);
        --accent-glow: rgba(16, 185, 129, 0.15);
        --card-bg: rgba(255, 255, 255, 0.85);
        --card-border: rgba(226, 232, 240, 0.8);
        --text-main: #0f172a;
        --text-sub: #475569;
        --legal-tag-bg: #ecfdf5;
        --legal-tag-color: #065f46;
        --news-tag-bg: #eff6ff;
        --news-tag-color: #1e40af;
    }

    .stApp {
        background: radial-gradient(circle at 50% 0%, #f0fdf4 0%, #f8fafc 40%, #f1f5f9 100%);
        color: var(--text-main);
    }

    /* Container tối ưu chiều rộng */
    .block-container {
        max-width: 960px;
        padding-top: 1.5rem;
        padding-bottom: 7.5rem;
    }

    /* Sidebar thiết kế tối giản, sắc sảo */
    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid rgba(226, 232, 240, 0.8);
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.02);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.2rem;
    }

    /* Tiêu đề sidebar & Brand mark */
    .brand-header {
        display: flex;
        align-items: center;
        gap: 0.85rem;
        padding: 0.6rem 0.4rem;
        margin-bottom: 0.5rem;
    }

    .brand-icon {
        width: 42px;
        height: 42px;
        border-radius: 12px;
        background: var(--primary-gradient);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35);
        color: white;
    }

    .brand-title {
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #0f172a;
        line-height: 1.2;
    }

    .brand-subtitle {
        font-size: 0.76rem;
        color: #64748b;
        font-weight: 500;
    }

    /* Section Tag trên sidebar */
    .sidebar-section-title {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
        margin: 1.1rem 0 0.4rem 0;
    }

    /* Badge thông tin hệ thống */
    .metric-badge {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.45rem 0.75rem;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        font-size: 0.82rem;
        margin-bottom: 0.35rem;
    }

    .metric-name {
        color: #64748b;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    .metric-value {
        font-weight: 600;
        color: #0f172a;
    }

    /* Hero header */
    .hero-container {
        text-align: center;
        padding: 4.5rem 1rem 2.5rem;
    }

    .hero-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.3rem 0.85rem;
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.25);
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #059669;
        margin-bottom: 1rem;
    }

    .hero-title {
        font-size: 2.25rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        color: #0f172a;
        margin-bottom: 0.6rem;
        line-height: 1.25;
    }

    .hero-subtitle {
        font-size: 1rem;
        color: #475569;
        max-width: 580px;
        margin: 0 auto 2rem;
        line-height: 1.6;
    }

    /* Khung thẻ câu hỏi gợi ý */
    .suggestion-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.75rem;
        font-size: 0.9rem;
        font-weight: 500;
        color: #1e293b;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
        cursor: pointer;
    }

    /* Source / Citation Card Style */
    .citation-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1rem;
        margin-top: 0.75rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }

    .citation-card:hover {
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.06);
    }

    .citation-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 0.5rem;
        gap: 0.5rem;
    }

    .citation-title {
        font-weight: 700;
        font-size: 0.95rem;
        color: #0f172a;
        line-height: 1.4;
    }

    .citation-badge-group {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        flex-wrap: wrap;
    }

    .tag-badge {
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.2rem 0.55rem;
        border-radius: 6px;
        letter-spacing: 0.02em;
    }

    .tag-legal {
        background: var(--legal-tag-bg);
        color: var(--legal-tag-color);
        border: 1px solid rgba(5, 150, 105, 0.2);
    }

    .tag-news {
        background: var(--news-tag-bg);
        color: var(--news-tag-color);
        border: 1px solid rgba(37, 99, 235, 0.2);
    }

    .tag-method {
        background: #f1f5f9;
        color: #475569;
        border: 1px solid #cbd5e1;
    }

    .citation-content {
        font-size: 0.86rem;
        color: #334155;
        line-height: 1.6;
        background: #f8fafc;
        border-left: 3px solid #10b981;
        padding: 0.6rem 0.85rem;
        border-radius: 0 8px 8px 0;
        margin: 0.6rem 0 0.4rem;
    }

    .citation-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 0.78rem;
        color: #64748b;
        margin-top: 0.4rem;
    }

    .citation-link {
        color: #059669;
        text-decoration: none;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
    }

    .citation-link:hover {
        text-decoration: underline;
    }

    /* Tinh chỉnh khung chat */
    [data-testid="stChatMessage"] {
        padding: 1.1rem 0.5rem;
        background: transparent;
    }

    [data-testid="stChatMessageContent"] {
        font-size: 0.98rem;
        line-height: 1.75;
        color: #1e293b;
    }

    /* Input chat dính đáy cố định sang trọng */
    [data-testid="stChatInput"] {
        max-width: 900px;
        margin: 0 auto;
    }

    [data-testid="stChatInput"] textarea {
        border-radius: 18px !important;
        border: 1.5px solid #cbd5e1 !important;
        box-shadow: 0 12px 36px rgba(0, 0, 0, 0.08) !important;
        background: #ffffff !important;
        padding: 0.85rem 1.2rem !important;
        font-size: 0.96rem !important;
    }

    [data-testid="stChatInput"] textarea:focus {
        border-color: #10b981 !important;
        box-shadow: 0 12px 36px rgba(16, 185, 129, 0.15) !important;
    }

    /* Dark Mode */
    @media (prefers-color-scheme: dark) {
        .stApp {
            background: radial-gradient(circle at 50% 0%, #064e3b 0%, #0f172a 45%, #020617 100%);
            color: #f8fafc;
        }
        [data-testid="stSidebar"] {
            background: #0f172a;
            border-right-color: #1e293b;
        }
        .brand-title { color: #f8fafc; }
        .brand-subtitle { color: #94a3b8; }
        .metric-badge {
            background: #1e293b;
            border-color: #334155;
        }
        .metric-name { color: #94a3b8; }
        .metric-value { color: #f8fafc; }
        .hero-title { color: #f8fafc; }
        .hero-subtitle { color: #cbd5e1; }
        .citation-card {
            background: #1e293b;
            border-color: #334155;
        }
        .citation-title { color: #f8fafc; }
        .citation-content {
            background: #0f172a;
            color: #cbd5e1;
        }
        [data-testid="stChatInput"] textarea {
            background: #1e293b !important;
            border-color: #334155 !important;
            color: #f8fafc !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Khởi tạo state hội thoại
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


def reset_chat() -> None:
    st.session_state.messages = []
    st.session_state.pending_prompt = None


def format_method_badge(method: str) -> str:
    """Trả về icon và nhãn tương ứng cho từng retrieval method."""
    method = (method or "unknown").lower()
    if method == "hybrid":
        return "🔀 Hybrid RRF"
    if method == "dense":
        return "⚡ Vector Dense"
    if method == "bm25":
        return "🔍 Từ khóa BM25"
    if method == "pageindex":
        return "📑 PageIndex Fallback"
    return f"📌 {method}"


def render_sources(sources: list[dict], retrieval_source: str) -> None:
    """Hiển thị nguồn dẫn dưới dạng card trực quan và chuyên nghiệp."""
    if not sources:
        return

    method_label = format_method_badge(retrieval_source)
    expander_title = f"📚 Nguồn tài liệu căn cứ ({len(sources)} trích dẫn · {method_label})"

    with st.expander(expander_title, expanded=False):
        for index, source in enumerate(sources, 1):
            metadata = source.get("metadata", {})
            title = metadata.get("title") or metadata.get("source") or f"Tài liệu #{index}"
            url = metadata.get("url")
            doc_type = metadata.get("doc_type", "legal")
            method = source.get("retrieval_method", "dense")
            score = float(source.get("score", 0.0))

            # Xác định nhãn doc_type
            if doc_type == "legal":
                type_tag = '<span class="tag-badge tag-legal">📜 Văn bản QPPL</span>'
            elif doc_type == "news":
                type_tag = '<span class="tag-badge tag-news">📰 Báo Chính Phủ</span>'
            else:
                type_tag = f'<span class="tag-badge tag-method">{html.escape(doc_type)}</span>'

            method_tag = f'<span class="tag-badge tag-method">{format_method_badge(method)}</span>'
            score_tag = f'<span class="tag-badge tag-method">Score: {score:.4f}</span>'

            url_html = (
                f'<a href="{url}" target="_blank" class="citation-link">↗ Mở liên kết gốc</a>'
                if url
                else '<span style="color:#94a3b8; font-size:0.75rem;">📁 Lưu trữ nội bộ</span>'
            )

            raw_preview = source.get("content", "").strip().replace("\n", " ")
            preview_clean = html.escape(raw_preview[:380] + ("…" if len(raw_preview) > 380 else ""))

            card_html = f"""
            <div class="citation-card">
                <div class="citation-header">
                    <div class="citation-title">[{index}] {html.escape(title)}</div>
                    <div class="citation-badge-group">
                        {type_tag}
                        {method_tag}
                        {score_tag}
                    </div>
                </div>
                <div class="citation-content">"{preview_clean}"</div>
                <div class="citation-footer">
                    <span>Nguồn: <code>{html.escape(str(metadata.get('source', '')))}</code></span>
                    {url_html}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)


# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown(
        """
        <div class="brand-header">
            <div class="brand-icon">⚖️</div>
            <div>
                <div class="brand-title">Luật Giao Thông AI</div>
                <div class="brand-subtitle">Trợ lý Pháp lý & Tra cứu</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.button("＋ Cuộc trò chuyện mới", use_container_width=True, on_click=reset_chat)

    st.markdown('<div class="sidebar-section-title">Thông số Pipeline</div>', unsafe_allow_html=True)
    top_k = st.slider("Số lượng tài liệu (Top-K)", min_value=3, max_value=10, value=5)

    provider_name = os.getenv("LLM_PROVIDER", "gemini").upper()
    model_name = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    emb_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

    st.markdown(
        f"""
        <div class="metric-badge">
            <span class="metric-name">🤖 LLM Model</span>
            <span class="metric-value">{provider_name} ({model_name})</span>
        </div>
        <div class="metric-badge">
            <span class="metric-name">🧬 Embeddings</span>
            <span class="metric-value">bge-m3 (1024d)</span>
        </div>
        <div class="metric-badge">
            <span class="metric-name">🗄️ Database</span>
            <span class="metric-value">ChromaDB + BM25</span>
        </div>
        <div class="metric-badge">
            <span class="metric-name">🔀 Fusion Strategy</span>
            <span class="metric-value">RRF (k=60)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.messages:
        st.markdown('<div class="sidebar-section-title">Lịch sử câu hỏi</div>', unsafe_allow_html=True)
        user_history = [m for m in st.session_state.messages if m["role"] == "user"]
        for idx, item in enumerate(user_history[-5:], 1):
            short_q = item["content"][:36] + ("…" if len(item["content"]) > 36 else "")
            st.caption(f"{idx}. {short_q}")

    st.divider()
    st.caption("Khóa học: AI in Action — VinUni | K4 Lab Day 8")


# ==========================================
# MAIN CONTENT AREA
# ==========================================

# Màn hình mở đầu khi chưa có tin nhắn
if not st.session_state.messages:
    st.markdown(
        """
        <div class="hero-container">
            <div class="hero-pill">⚡ Powered by Hybrid RAG & Citation Grounding</div>
            <h1 class="hero-title">Tra cứu Luật Giao thông Đường bộ</h1>
            <p class="hero-subtitle">
                Hỏi đáp chính xác về quy định đào tạo lái xe, trừ điểm GPLX, điều kiện kinh doanh vận tải và xử phạt vi phạm giao thông dựa trên nguồn chính thống.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("##### 💡 Câu hỏi mẫu thường gặp:")
    suggestions = [
        ("🚗 Điều kiện đào tạo lái xe", "Điều kiện để hoàn thành khóa đào tạo lái xe theo quy định mới là gì?"),
        ("🪪 Thời hạn cấp bằng lái xe", "Thời hạn cấp giấy phép lái xe sau khi đạt sát hạch là bao nhiêu ngày?"),
        ("🚸 Thiết bị an toàn trẻ em", "Quy định xử phạt khi chở trẻ em dưới 10 tuổi trên ô tô không có thiết bị an toàn?"),
        ("📹 Camera trên xe vận tải", "Xe ô tô kinh doanh vận tải hành khách phải lắp camera trong khoang hành khách thế nào?"),
    ]

    cols = st.columns(2)
    for i, (label, query) in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(f"**{label}**\n\n{query}", key=f"sug_{i}", use_container_width=True):
                st.session_state.pending_prompt = query
                st.rerun()

# Hiển thị lịch sử chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources(message.get("sources", []), message.get("retrieval_source", "none"))

# Xử lý input từ người dùng
typed_prompt = st.chat_input("Nhập câu hỏi về quy định, mức phạt, giấy phép lái xe…")
prompt = st.session_state.pending_prompt or typed_prompt
st.session_state.pending_prompt = None

if prompt:
    # 1. Hiển thị câu hỏi của User
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Xử lý câu trả lời từ Assistant
    with st.chat_message("assistant"):
        with st.spinner("Đang truy xuất văn bản pháp luật và tổng hợp câu trả lời…"):
            try:
                result = generate_with_citation(prompt, top_k=top_k)
            except Exception as error:
                result = {
                    "answer": (
                        "⚠️ Hệ thống truy xuất tạm thời chưa hoàn tất phản hồi. "
                        "Vui lòng kiểm tra lại ChromaDB, vector embeddings và cấu hình API Key trong file `.env`."
                    ),
                    "sources": [],
                    "retrieval_source": "none",
                }
                st.caption(f"Chi tiết kỹ thuật: `{type(error).__name__}: {error}`")

        st.markdown(result["answer"])
        render_sources(result["sources"], result["retrieval_source"])

    # Lưu lại lịch sử câu trả lời
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
            "retrieval_source": result["retrieval_source"],
        }
    )
