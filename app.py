import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="RAG Chatbot",
    layout="wide",
)


def show_sources(sources: list[dict], retrieval_source: str) -> None:
    """Show the exact chunk IDs used for citations and their retrieval details."""
    if not sources:
        return

    with st.expander(f"Nguồn tham khảo ({len(sources)})"):
        st.caption(f"Nguồn truy hồi: {retrieval_source}")
        for source in sources:
            metadata = source["metadata"]
            st.write(metadata["title"])
            st.caption(
                f"Citation: [{source['id']}] · Tệp: {metadata['source']} · "
                f"Phương thức: {source['retrieval_method']} · "
                f"Điểm truy hồi: {source['score']:.4f}"
            )
            if metadata.get("url"):
                st.write(metadata["url"])
            st.write(source["content"])
            st.divider()


if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("RAG Chatbot")
    st.caption("Hỏi đáp dựa trên bộ tài liệu đã lập chỉ mục.")
    top_k = st.slider("Số chunks", 3, 10, 5)

st.title("RAG Chatbot")
st.caption("Nhập câu hỏi để nhận câu trả lời kèm citation và nguồn kiểm chứng.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            show_sources(
                message.get("sources", []),
                message.get("retrieval_source", "none"),
            )

query = st.chat_input("Nhập câu hỏi...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm nguồn và tạo câu trả lời..."):
            result = generate_with_citation(query, top_k=top_k)
        st.markdown(result["answer"])
        show_sources(result["sources"], result["retrieval_source"])

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
        "retrieval_source": result["retrieval_source"],
    })
