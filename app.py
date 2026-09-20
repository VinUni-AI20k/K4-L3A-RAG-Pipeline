"""Streamlit UI for the Physics 10–12 grounded RAG chatbot."""

from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

from src.task10_generation import generate_with_citation


st.set_page_config(page_title="Vật lí 10–12 RAG", page_icon="📚", layout="wide")
SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."


def render_sources(sources: list[dict], retrieval_source: str | None = None) -> None:
    """Render source metadata and the cited chunk content."""
    if not sources:
        return
    with st.expander(f"Nguồn tham khảo ({len(sources)})", expanded=False):
        if retrieval_source:
            st.caption(f"Retrieval: {retrieval_source}")
        for index, source in enumerate(sources, 1):
            metadata = source["metadata"]
            title = metadata.get("title", metadata.get("source", source["id"]))
            page = metadata.get("pdf_page")
            page_label = f" · PDF page {page}" if page else ""
            st.markdown(f"**[Document {index}] {title}**")
            st.caption(
                f"{metadata.get('source', source['id'])}{page_label} · "
                f"method={source.get('retrieval_method', 'unknown')} · "
                f"score={float(source.get('score', 0.0)):.4f}"
            )
            if metadata.get("url"):
                st.markdown(f"Source URL: {metadata['url']}")
            with st.container(border=True):
                st.write(source["content"])


if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("Vật lí 10–12")
    st.caption("Hỏi đáp dựa trên sách giáo khoa và nguồn tham khảo công khai.")
    top_k = st.slider("Số chunks truy xuất", min_value=3, max_value=10, value=5)
    if st.button("Xóa lịch sử"):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.caption("Embedding: OpenAI text-embedding-3-small")
    st.caption("Generator: OpenAI gpt-4o-mini")

st.title("Chatbot Vật lí 10–12")
st.caption("Câu trả lời được giới hạn trong nguồn dữ liệu và đi kèm citation.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources(message.get("sources", []), message.get("retrieval_source"))

query = st.chat_input("Ví dụ: Động năng của một vật là gì?")
if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    with st.chat_message("assistant"):
        with st.spinner("Đang tìm tài liệu và tạo câu trả lời..."):
            try:
                result = generate_with_citation(query, top_k=top_k)
            except Exception:
                result = {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}
        answer = result["answer"]
        st.markdown(answer)
        render_sources(result["sources"], result["retrieval_source"])
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": result["sources"],
            "retrieval_source": result["retrieval_source"],
        }
    )
