import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="PTIT",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("RAG Chatbot")
    st.caption("Chatbot RAG cho corpus tuyển sinh và thông tin PTIT.")
    top_k = st.slider("Số chunks", 3, 10, 5)

st.title("PTIT RAG Chatbot")
st.caption("Hỏi đáp dựa trên tài liệu đã thu thập và index trong lab.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        for source in message.get("sources", []):
            metadata = source["metadata"]
            with st.expander(
                f"{metadata['source']} | {source['retrieval_method']} | "
                f"{source['score']:.4f}"
            ):
                st.caption(f"Title: {metadata['title']}")
                st.write(source["content"])

query = st.chat_input("Nhập câu hỏi...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        result = generate_with_citation(query, top_k=top_k)
        answer = result["answer"]
        sources = result["sources"]
        st.markdown(answer)

        st.caption(f"Retrieval source: {result['retrieval_source']}")
        for source in sources:
            metadata = source["metadata"]
            with st.expander(
                f"{metadata['source']} | {source['retrieval_method']} | "
                f"{source['score']:.4f}"
            ):
                st.caption(f"Title: {metadata['title']}")
                st.write(source["content"])

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
    })
