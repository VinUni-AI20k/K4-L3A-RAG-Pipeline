import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="Chatbot Du lịch Việt Nam",
    page_icon="",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []


def render_sources(sources: list[dict], retrieval_source: str) -> None:
    """Hiển thị nguồn, retrieval method và score của từng chunk."""
    if not sources:
        st.caption("Không có nguồn nào được sử dụng.")
        return
    st.caption(f"Retrieval source: `{retrieval_source}`")
    with st.expander(f"Nguồn đã dùng ({len(sources)})"):
        for index, source in enumerate(sources, 1):
            metadata = source["metadata"]
            st.markdown(
                f"**[Document {index}] {metadata['title']}** — `{metadata['source']}` "
                f"(chunk {metadata['chunk_index']}, "
                f"method `{source['retrieval_method']}`, score `{source['score']:.4f}`)"
            )
            if metadata.get("url"):
                st.markdown(f"[Link nguồn]({metadata['url']})")
            st.text(source["content"][:500])


with st.sidebar:
    st.title("Chatbot Du lịch Việt Nam")
    st.caption(
        "Hỏi đáp trên corpus của nhóm: văn bản chính sách du lịch và "
        "bài viết về điểm đến, văn hoá, ẩm thực Việt Nam."
    )
    top_k = st.slider("Số chunks", 3, 10, 5)
    if st.button("Xoá hội thoại"):
        st.session_state.messages = []

st.title("Chatbot Du lịch Việt Nam")
st.caption(
    "Hybrid retrieval (dense + BM25 + RRF), fallback PageIndex và câu trả lời có citation."
)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources(
                message.get("sources", []), message.get("retrieval_source", "none")
            )

query = st.chat_input("Nhập câu hỏi...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang truy hồi và tổng hợp câu trả lời..."):
            try:
                result = generate_with_citation(query, top_k)
            except Exception as error:  # UI không được crash vì lỗi provider
                result = {
                    "answer": f"Có lỗi khi tạo câu trả lời: {error}",
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
