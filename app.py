import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation

load_dotenv()

st.set_page_config(
    page_title="RAG Chatbot - Du lich Vinh Ha Long",
    page_icon="",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("RAG Chatbot")
    st.caption("Hoi dap tu chinh sach va bai viet cong khai ve du lich Vinh Ha Long")
    top_k = st.slider("So chunks", 3, 10, 5)
    st.divider()
    st.caption("Hybrid retrieval: dense + BM25 + RRF.")

st.title("RAG Chatbot - Du lich Vinh Ha Long")
st.caption("Tra loi dua tren van ban quyet dinh/quy dinh va bai viet cong khai da thu thap.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("sources"):
            with st.expander("Nguon trich xuat", expanded=False):
                for index, source in enumerate(message["sources"], 1):
                    metadata = source.get("metadata", {})
                    title = metadata.get("title", "Khong ro")
                    source_name = metadata.get("source", "Khong ro")
                    score = source.get("score", 0.0)
                    method = source.get("retrieval_method", "unknown")
                    st.markdown(f"**{index}. {title}** | file: `{source_name}` | score: `{score:.4f}` | method: `{method}`")

query = st.chat_input("Hoi ve Vinh Ha Long, quy dinh du lich, visa...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Dang truy xuat..."):
            result = generate_with_citation(query, top_k=top_k)

        answer = result["answer"]
        sources = result["sources"]
        st.markdown(answer)

        if sources:
            with st.expander("Nguon trich xuat", expanded=False):
                for index, source in enumerate(sources, 1):
                    metadata = source.get("metadata", {})
                    title = metadata.get("title", "Khong ro")
                    source_name = metadata.get("source", "Khong ro")
                    score = source.get("score", 0.0)
                    method = source.get("retrieval_method", "unknown")
                    st.markdown(f"**{index}. {title}** | file: `{source_name}` | score: `{score:.4f}` | method: `{method}`")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
        }
    )
