import html
import re
import time
import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import (
    generate_with_citation,
    generate_with_history,
)


load_dotenv()

st.set_page_config(
    page_title="Hệ thống Trợ lý Pháp luật & Tái cơ cấu Doanh nghiệp (RAG)",
    page_icon="⚖️",
    layout="wide",
)

# Khởi tạo session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "input_query" not in st.session_state:
    st.session_state.input_query = ""


def highlight_citations(text: str) -> str:
    """Thay thế các thẻ trích dẫn [Document X] thành badge nổi bật trong UI (Bonus UI Highlighting)."""
    badge_template = (
        r'<span style="background-color: #dbeafe; color: #1e40af; '
        r'padding: 2px 8px; border-radius: 12px; font-weight: 600; '
        r'font-size: 0.85em; border: 1px solid #bfdbfe; display: inline-flex; align-items: center; gap: 4px;">'
        r'📄 Document \1</span>'
    )
    # Match [Document 1], [Document 2], [Doc 1], (Document 1)
    highlighted = re.sub(
        r"\[(?:Document|Doc)\s*(\d+)\]",
        badge_template,
        text,
        flags=re.IGNORECASE,
    )
    highlighted = re.sub(
        r"\((?:Document|Doc)\s*(\d+)\)",
        badge_template,
        highlighted,
        flags=re.IGNORECASE,
    )
    return highlighted


def render_sources_expander(sources: list[dict], retrieval_source: str):
    """Hiển thị chi tiết từng nguồn tài liệu tham khảo kèm metadata, score và liên kết trích dẫn."""
    if not sources:
        return

    method_labels = {
        "hybrid": "🔥 Hybrid (Dense + BM25 RRF)",
        "dense": "🔍 Dense Semantic Search",
        "bm25": "📝 BM25 Lexical Search",
        "pageindex": "📑 PageIndex Vectorless Fallback",
        "none": "🚫 Không có nguồn",
    }
    method_badge = method_labels.get(retrieval_source, retrieval_source.upper())

    with st.expander(
        f"📚 Nguồn tham khảo ({len(sources)} đoạn trích) • Chiến lược: {method_badge}",
        expanded=False,
    ):
        for idx, src in enumerate(sources, 1):
            meta = src.get("metadata", {})
            title = meta.get("title", "Tài liệu không tên")
            source_file = meta.get("source", "Không rõ nguồn")
            doc_type = meta.get("doc_type", "Chung")
            chunk_idx = meta.get("chunk_index", 0)
            score = src.get("score", 0.0)
            method = src.get("retrieval_method", "hybrid")
            url = meta.get("url")

            type_color = "#15803d" if doc_type == "legal" else "#0369a1"
            type_label = "Văn bản pháp luật" if doc_type == "legal" else "Báo chí / Tin tức"

            st.markdown(
                f"""
                <div style="background-color: #f8fafc; border-left: 4px solid #3b82f6; border-radius: 6px; padding: 10px 14px; margin-bottom: 12px; border: 1px solid #e2e8f0; border-left-width: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-weight: 700; color: #1e293b; font-size: 0.95em;">
                            📄 [Document {idx}] {html.escape(title)}
                        </span>
                        <span style="background-color: #f1f5f9; color: #475569; padding: 2px 6px; border-radius: 4px; font-size: 0.78em; font-weight: 600;">
                            Score: {score:.4f} ({method})
                        </span>
                    </div>
                    <div style="font-size: 0.82em; color: #64748b; margin-bottom: 8px;">
                        📁 <b>Tệp:</b> <code>{html.escape(source_file)}</code> &nbsp;|&nbsp; 
                        🏷️ <b>Loại:</b> <span style="color: {type_color}; font-weight: 600;">{type_label}</span> &nbsp;|&nbsp; 
                        🔢 <b>Đoạn:</b> #{chunk_idx}
                        {f' &nbsp;|&nbsp; 🔗 <a href="{html.escape(url)}" target="_blank" style="color: #2563eb; text-decoration: none;">Xem nguồn gốc</a>' if url else ''}
                    </div>
                    <div style="background-color: #ffffff; padding: 8px 12px; border-radius: 4px; border: 1px solid #cbd5e1; font-size: 0.88em; line-height: 1.5; color: #334155; font-style: italic;">
                        "{html.escape(src.get('content', ''))}"
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Cấu hình Hệ thống RAG")
    st.markdown(
        "**Đề tài:** Tra cứu quy định pháp luật về Tái cơ cấu Doanh nghiệp Nhà nước & Xử lý nợ xấu "
        "(Nghị định 357, 358, 359/2026/NĐ-CP, VAMC, DATC)."
    )

    st.divider()
    top_k = st.slider("Số chunks truy xuất (top_k)", min_value=1, max_value=10, value=5)

    use_memory = st.toggle(
        "🧠 Conversation Memory",
        value=True,
        help="Kích hoạt bộ nhớ hội thoại đa lượt và tự động bổ sung ngữ cảnh cho các câu hỏi nối tiếp (follow-up questions).",
    )

    st.divider()
    st.markdown("### 📊 Thông tin Pipeline")
    st.markdown(
        """
        - **Embedding:** `text-embedding-3-small` (1536 dims)
        - **Vectorstore:** ChromaDB (`rag_documents`)
        - **Sparse Search:** BM25 (BM25Plus)
        - **Reranker:** Reciprocal Rank Fusion ($k=60$)
        - **LLM Generator:** `gpt-4o-mini`
        - **Fallback:** PageIndex Vectorless
        """
    )

    st.divider()
    if st.button("🗑️ Xóa toàn bộ lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# --- MAIN HEADER ---
st.title("⚖️ Trợ lý Tra cứu Pháp lý & Tái cơ cấu Doanh nghiệp")
st.caption(
    "Hệ thống Hybrid RAG kết hợp Semantic Search, BM25 Lexical Search & RRF Reranking. "
    "Mọi khẳng định đều có trích dẫn nguồn đối chiếu và cơ chế safe refusal an toàn."
)

# --- QUICK PROMPT PILLS ---
st.markdown("**💡 Câu hỏi mẫu thử nghiệm nhanh:**")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏛️ Vốn điều lệ & Quản lý VAMC", use_container_width=True):
        st.session_state.input_query = "VAMC có số vốn điều lệ là bao nhiêu và do ai quản lý?"
with col2:
    if st.button("🏢 Vai trò của DATC (NĐ 358)", use_container_width=True):
        st.session_state.input_query = "Nghị định 358/2026 quy định vai trò và cơ chế tài chính của DATC như thế nào?"
with col3:
    if st.button("🚫 Thử câu hỏi ngoài miền (Refusal)", use_container_width=True):
        st.session_state.input_query = "Thời tiết hôm nay ở Sa Pa thế nào?"


# --- RENDER CHAT HISTORY ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        highlighted = highlight_citations(message["content"])
        st.markdown(highlighted, unsafe_allow_html=True)
        if message.get("sources"):
            render_sources_expander(message["sources"], message.get("retrieval_source", "hybrid"))


# --- CHAT INPUT & GENERATION ---
query_input = st.chat_input("Nhập câu hỏi cần tra cứu pháp lý...")
query = query_input or st.session_state.input_query
if query:
    st.session_state.input_query = ""

    # 1. Thêm câu hỏi người dùng
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # 2. Xử lý sinh câu trả lời
    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm văn bản pháp lý và tổng hợp câu trả lời..."):
            if use_memory and len(st.session_state.messages) > 1:
                # Dùng conversation memory cho multi-turn
                result = generate_with_history(
                    query=query,
                    history=st.session_state.messages[:-1],
                    top_k=top_k,
                )
            else:
                result = generate_with_citation(query=query, top_k=top_k)

            answer = result["answer"]
            sources = result["sources"]
            retrieval_source = result["retrieval_source"]

            # Giả lập streaming mượt mà
            placeholder = st.empty()
            highlighted_full = highlight_citations(answer)

            # Stream nhẹ hiển thị text
            displayed_text = ""
            for char in answer:
                displayed_text += char
                if len(displayed_text) % 5 == 0 or len(displayed_text) == len(answer):
                    placeholder.markdown(highlight_citations(displayed_text), unsafe_allow_html=True)
                    time.sleep(0.005)

            placeholder.markdown(highlighted_full, unsafe_allow_html=True)

            # Render expander nguồn
            if sources:
                render_sources_expander(sources, retrieval_source)

    # 3. Lưu vào lịch sử phiên làm việc
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "retrieval_source": retrieval_source,
    })
