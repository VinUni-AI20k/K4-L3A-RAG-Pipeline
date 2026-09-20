import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_stream


load_dotenv()

st.set_page_config(
    page_title="IELTS Writing AI Assistant",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS phong cách OpenAI ChatGPT kết hợp Theme IELTS & Watermark mờ
st.markdown("""
<style>
    /* Google Font hiện đại */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Container chính độ rộng chuẩn ChatGPT (768px) căn giữa */
    .main .block-container {
        max-width: 768px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 7rem !important;
    }

    /* Hình nền mờ Watermark chữ IELTS tinh tế, nhẹ nhàng */
    [data-testid="stAppViewContainer"] {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 600" width="1000" height="600"><text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="160" fill="%23e01a22" opacity="0.03" letter-spacing="18">IELTS</text><text x="50%" y="64%" text-anchor="middle" dominant-baseline="middle" font-family="system-ui, -apple-system, sans-serif" font-weight="700" font-size="24" fill="%23002f6c" opacity="0.025" letter-spacing="12">WRITING ASSISTANT</text></svg>');
        background-repeat: no-repeat;
        background-position: center 42%;
        background-attachment: fixed;
        background-size: 720px auto;
    }

    /* Chat message container kiểu ChatGPT */
    [data-testid="stChatMessage"] {
        padding: 0.6rem 0.8rem !important;
        border-radius: 20px !important;
        margin-bottom: 1.25rem !important;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
    }

    /* Khung chat của User: Bo tròn dạng viên thuốc (Pill bubble) chuẩn OpenAI */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background-color: rgba(128, 128, 128, 0.1) !important;
        border-radius: 24px !important;
        padding: 10px 18px !important;
        max-width: 82% !important;
        margin-left: auto !important;
        border: 1px solid rgba(224, 26, 34, 0.15) !important;
    }

    /* Khung chat của Assistant: Canvas phẳng thoáng, chữ rõ ràng không viền như ChatGPT */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background-color: transparent !important;
        border: none !important;
        padding: 8px 4px !important;
        max-width: 100% !important;
    }

    /* Avatar bo tròn tinh tế */
    [data-testid="stChatMessageAvatar"] {
        border-radius: 50% !important;
        overflow: hidden !important;
    }

    /* Khung nhập liệu (Chat Input) bo tròn viên thuốc kiểu OpenAI ChatGPT */
    [data-testid="stChatInput"] {
        max-width: 768px !important;
        margin: 0 auto !important;
        border-radius: 30px !important;
        border: 1.5px solid rgba(128, 128, 128, 0.3) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.07) !important;
        background-color: var(--secondary-background-color) !important;
        transition: all 0.25s ease !important;
    }

    [data-testid="stChatInput"]:focus-within {
        border-color: #e01a22 !important;
        box-shadow: 0 0 0 2px rgba(224, 26, 34, 0.18), 0 6px 24px rgba(0, 0, 0, 0.1) !important;
    }

    /* XÓA BỎ HOÀN TOÀN VIỀN BÊN TRONG: Chỉ để duy nhất viền ở phần bo tròn bên ngoài */
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] div,
    [data-testid="stChatInput"] div:focus,
    [data-testid="stChatInput"] div:focus-within,
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInput"] textarea:focus,
    [data-testid="stChatInput"] textarea:focus-visible {
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }

    [data-testid="stChatInput"] textarea {
        font-size: 15px !important;
        padding-top: 10px !important;
        padding-bottom: 10px !important;
        padding-left: 16px !important;
    }

    /* Nút gửi bo tròn dạng hình tròn chuẩn ChatGPT */
    [data-testid="stChatInput"] button {
        border-radius: 50% !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        margin-right: 6px !important;
    }

    /* Nút tạo chat mới trong Sidebar kiểu ChatGPT */
    .stButton > button {
        border-radius: 22px !important;
        border: 1px solid rgba(128, 128, 128, 0.25) !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        border-color: #e01a22 !important;
        color: #e01a22 !important;
    }

    /* Expander nguồn trích dẫn bo tròn gọn gàng */
    [data-testid="stExpander"] {
        border-radius: 14px !important;
        border: 1px solid rgba(128, 128, 128, 0.18) !important;
        overflow: hidden !important;
        margin-top: 0.5rem !important;
    }


</style>
""", unsafe_allow_html=True)

# Khởi tạo session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar cấu hình kiểu ChatGPT
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
        <span style="background: #e01a22; color: white; font-weight: 900; font-size: 1.05rem; padding: 2px 8px; border-radius: 4px;">IELTS</span>
        <span style="font-size: 1.15rem; font-weight: 700;">Writing Lab</span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("➕ Đoạn chat mới", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.caption("Trợ lý tra cứu tiêu chí Band Descriptors & bài mẫu IELTS Writing.")
    st.divider()

    top_k = st.slider("Số chunks truy xuất (top_k)", 3, 10, 5)

    st.markdown("**Kiến trúc RAG:**")
    st.markdown("- 🚀 **LLM**: `gemini-3.5-flash-lite` *(Streaming ~1.2s)*")
    st.markdown("- 🔍 **Dense**: `gemini-embedding-001` *(3072 dims)*")
    st.markdown("- 📑 **Sparse**: BM25 Okapi *(In-Memory Cache)*")
    st.markdown("- ⚖️ **Reranking**: Reciprocal Rank Fusion (RRF)")

    st.divider()
    st.markdown("**4 Tiêu chí chấm điểm Writing:**")
    st.markdown("- 🎯 **TR / TA**: Task Response & Achievement")
    st.markdown("- 🔗 **CC**: Coherence & Cohesion")
    st.markdown("- 📖 **LR**: Lexical Resource")
    st.markdown("- ⚖️ **GRA**: Grammatical Range & Accuracy")


# Màn hình chào mừng phong cách OpenAI ChatGPT khi chưa có tin nhắn
if len(st.session_state.messages) == 0:
    st.markdown("""
    <div style="text-align: center; margin-top: 5rem; margin-bottom: 3rem;">
        <div style="display: inline-flex; align-items: center; justify-content: center; width: 60px; height: 60px; background: linear-gradient(135deg, #e01a22, #b91c1c); border-radius: 50%; box-shadow: 0 4px 16px rgba(224, 26, 34, 0.25); margin-bottom: 14px;">
            <span style="color: white; font-size: 26px;">✍️</span>
        </div>
        <h2 style="font-size: 1.55rem; font-weight: 700; margin-bottom: 6px;">Hôm nay bạn muốn luyện IELTS Writing gì?</h2>
        <p style="color: gray; font-size: 0.95rem; max-width: 500px; margin: 0 auto;">Tra cứu chuẩn xác tiêu chí chấm điểm Band 1.0 – 9.0, cấu trúc bài viết Task 1, Task 2 và chiến lược phòng thi.</p>
    </div>
    """, unsafe_allow_html=True)

# Hiển thị lịch sử hội thoại kiểu ChatGPT
for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "✍️"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        # TODO: Hiển thị sources và retrieval score.
        if message.get("sources"):
            with st.expander(f"📚 Nguồn trích dẫn ({message.get('retrieval_source', 'hybrid')})"):
                for idx, src in enumerate(message["sources"], 1):
                    meta = src.get("metadata", {})
                    st.markdown(f"**[{idx}] {meta.get('title', 'Tài liệu')}** (Nguồn: `{meta.get('source', '')}` | Score: `{src.get('score', 0):.4f}`)")
                    st.caption(src.get("content", ""))

# Thanh chat input bo tròn phong cách OpenAI
query = st.chat_input("Hỏi bất cứ điều gì về IELTS Writing (ví dụ: Tiêu chí Band 7 Task 2 gồm những gì?)...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user", avatar="👤"):
        st.markdown(query)

    with st.chat_message("assistant", avatar="✍️"):
        with st.spinner("Đang tìm kiếm tài liệu và đối chiếu tiêu chuẩn IELTS..."):
            # TODO: Gọi generate_with_citation(query, top_k).
            stream_gen, sources, retrieval_source = generate_stream(query, top_k=top_k)

        answer = st.write_stream(stream_gen)

        # TODO: Hiển thị sources và citation.
        if sources:
            with st.expander(f"📚 Nguồn trích dẫn ({retrieval_source})"):
                for idx, src in enumerate(sources, 1):
                    meta = src.get("metadata", {})
                    st.markdown(f"**[{idx}] {meta.get('title', 'Tài liệu')}** (Nguồn: `{meta.get('source', '')}` | Score: `{src.get('score', 0):.4f}`)")
                    st.caption(src.get("content", ""))

        # TODO: Lưu answer và sources vào session state.
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "retrieval_source": retrieval_source,
        })
