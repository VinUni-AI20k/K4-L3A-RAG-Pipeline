import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="Chatbot Du lịch Việt Nam",
    page_icon="🇻🇳",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []


def render_sources(sources: list[dict], retrieval_source: str) -> None:
    """Hiển thị nguồn, retrieval method và score của từng chunk đẹp hơn."""
    if not sources:
        st.info("ℹ️ Không có nguồn nào được sử dụng.")
        return

    # Badge for retrieval source
    color = "#28a745" if retrieval_source == "hybrid" else "#ffc107" if retrieval_source == "pageindex" else "#6c757d"
    badge_html = f'''
    <div style="margin-bottom: 10px;">
        <span style="background-color: {color}; color: white; padding: 4px 10px; border-radius: 15px; font-size: 13px; font-weight: 500;">
            🔍 Method: {retrieval_source.upper()}
        </span>
    </div>
    '''
    st.markdown(badge_html, unsafe_allow_html=True)

    with st.expander(f"📚 Nguồn đã dùng ({len(sources)})", expanded=False):
        tabs = st.tabs([f"Doc {i}" for i in range(1, len(sources) + 1)])
        for index, (tab, source) in enumerate(zip(tabs, sources), 1):
            with tab:
                metadata = source["metadata"]
                title = metadata.get('title', 'Unknown Title')
                file_source = metadata.get('source', 'Unknown Source')
                chunk_index = metadata.get('chunk_index', '?')
                method = source.get('retrieval_method', 'unknown')
                score = source.get('score', 0.0)
                url = metadata.get("url", "")
                
                # Header of the tab
                st.markdown(f"**{title}**")
                
                # Metadata cols
                col1, col2, col3 = st.columns(3)
                col1.caption(f"📄 **File:** `{file_source}`")
                col2.caption(f"🧩 **Chunk:** `{chunk_index}`")
                col3.caption(f"📈 **Score:** `{score:.4f}` ({method})")
                
                if url:
                    st.markdown(f"🔗 [Link bài viết gốc]({url})")
                
                # Content preview
                st.markdown("---")
                st.markdown(f"> *{source['content'][:600]}...*")


with st.sidebar:
    st.title("🇻🇳 Chatbot Du lịch Việt Nam")
    st.caption(
        "Hỏi đáp trên corpus của nhóm: văn bản chính sách du lịch và "
        "bài viết về điểm đến, văn hoá, ẩm thực Việt Nam."
    )
    st.divider()
    top_k = st.slider("Số chunks để truy hồi (top_k)", 3, 10, 5)
    st.divider()
    if st.button("🗑️ Xoá hội thoại", use_container_width=True):
        st.session_state.messages = []

st.title("🇻🇳 Chatbot Du lịch Việt Nam 🤖")
st.markdown(
    "*Hybrid retrieval (dense + BM25 + RRF), fallback PageIndex và câu trả lời có citation.*"
)
st.divider()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources(
                message.get("sources", []), message.get("retrieval_source", "none")
            )

query = st.chat_input("💬 Nhập câu hỏi về du lịch Việt Nam...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("⏳ Đang truy hồi và tổng hợp câu trả lời..."):
            try:
                result = generate_with_citation(query, top_k)
            except Exception as error:  # UI không được crash vì lỗi provider
                result = {
                    "answer": f"⚠️ Có lỗi khi tạo câu trả lời: {error}",
                    "sources": [],
                    "retrieval_source": "none",
                }
        st.markdown(result["answer"])
        render_sources(result["sources"], result["retrieval_source"])

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
            "retrieval_source": result["retrieval_source"],
        }
    )
