import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="Hệ thống Trợ lý Pháp luật Doanh nghiệp (RAG)",
    page_icon="⚖️",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("⚙️ Cấu hình RAG")
    st.markdown("**Chủ đề:** Tái cơ cấu doanh nghiệp nhà nước, xử lý nợ xấu (VAMC, DATC, NĐ 357, 358, 359/2026).")
    top_k = st.slider("Số chunks truy xuất (top_k)", 1, 10, 5)
    st.divider()
    if st.button("🗑️ Xóa lịch sử chat"):
        st.session_state.messages = []
        st.rerun()

st.title("⚖️ Trợ lý Tra cứu Pháp lý & Tái cơ cấu Doanh nghiệp")
st.caption("Hệ thống Hybrid RAG kết hợp Dense Search (OpenAI), BM25 (BM25Plus) & RRF Reranking.")

# Hiển thị lịch sử chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander(f"📚 Nguồn tham khảo ({len(message['sources'])} đoạn trích) - [{message.get('retrieval_source', 'hybrid')}]"):
                for idx, src in enumerate(message["sources"], 1):
                    meta = src.get("metadata", {})
                    st.markdown(f"**[{idx}] {meta.get('title', 'Tài liệu')}** (`{meta.get('source', '')}` - score: `{src.get('score', 0):.4f}`)")
                    st.markdown(f"> *{src.get('content', '')}*")

query = st.chat_input("Hỏi về quy định pháp luật (ví dụ: VAMC mua nợ xấu thế nào?)...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm tài liệu và sinh câu trả lời..."):
            result = generate_with_citation(query, top_k=top_k)
            answer = result["answer"]
            sources = result["sources"]
            retrieval_source = result["retrieval_source"]

            st.markdown(answer)

            if sources:
                with st.expander(f"📚 Nguồn tham khảo ({len(sources)} đoạn trích) - [{retrieval_source}]"):
                    for idx, src in enumerate(sources, 1):
                        meta = src.get("metadata", {})
                        st.markdown(f"**[{idx}] {meta.get('title', 'Tài liệu')}** (`{meta.get('source', '')}` - score: `{src.get('score', 0):.4f}`)")
                        st.markdown(f"> *{src.get('content', '')}*")

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "retrieval_source": retrieval_source,
    })
