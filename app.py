import streamlit as st
from dotenv import load_dotenv

from src.task9_retrieval_pipeline import RERANKER_ENABLED
from src.task10_generation import generate_with_citation
from src.task13_conversation_memory import answer_with_memory


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
    use_memory = st.toggle("Nhớ hội thoại (follow-up)", value=True)
    if st.button("Xoá hội thoại"):
        st.session_state.messages = []
        st.rerun()
    st.caption(
        "Retrieval: dense + BM25 → RRF"
        + (" → cross-encoder rerank" if RERANKER_ENABLED else "")
        + " → PageIndex fallback"
    )

st.title("RAG Chatbot")
st.caption("Nhập câu hỏi để nhận câu trả lời kèm citation và nguồn kiểm chứng.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            if message.get("standalone_query"):
                st.caption(f"Câu hỏi đã diễn giải: {message['standalone_query']}")
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
            # Lịch sử là các lượt trước lượt user vừa thêm.
            history = st.session_state.messages[:-1]
            if use_memory and history:
                result = answer_with_memory(query, history, top_k=top_k)
            else:
                result = generate_with_citation(query, top_k=top_k)
        standalone = result.get("standalone_query")
        if standalone and standalone != query:
            st.caption(f"Câu hỏi đã diễn giải: {standalone}")
        else:
            standalone = None
        st.markdown(result["answer"])
        show_sources(result["sources"], result["retrieval_source"])

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
        "retrieval_source": result["retrieval_source"],
        "standalone_query": standalone,
    })
