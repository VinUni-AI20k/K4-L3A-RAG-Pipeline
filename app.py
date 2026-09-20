import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []


def render_sources(sources: list[dict], retrieval_source: str | None) -> None:
    if not sources:
        return
    if retrieval_source:
        st.caption(f"Retrieval: {retrieval_source}")
    with st.expander(f"Nguồn đã dùng ({len(sources)})"):
        for index, source in enumerate(sources, 1):
            metadata = source["metadata"]
            st.markdown(f"**[{index}] {metadata['title']}**")
            st.caption(
                f"{metadata['source']} · {source['retrieval_method']} · "
                f"score: {source['score']:.4f}"
            )
            if metadata.get("url"):
                st.link_button("Mở nguồn", metadata["url"])

with st.sidebar:
    st.title("RAG Chatbot")
    st.caption("Hỏi đáp dựa trên bộ tài liệu của nhóm, có nguồn kiểm chứng.")
    top_k = st.slider("Số chunks", 3, 10, 5)

st.title("RAG Chatbot")
st.caption("Đặt câu hỏi về chủ đề tài liệu. Câu trả lời chỉ dùng evidence đã truy xuất.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        render_sources(message.get("sources", []), message.get("retrieval_source"))

query = st.chat_input("Nhập câu hỏi...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm nguồn và tạo câu trả lời..."):
            result = generate_with_citation(query, top_k=top_k)
        answer = result["answer"]
        sources = result["sources"]
        st.markdown(answer)
        render_sources(sources, result["retrieval_source"])

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "retrieval_source": result["retrieval_source"],
        }
    )
