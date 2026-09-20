import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation

load_dotenv()
st.set_page_config(page_title="Vat ly 10-12 | RAG Chatbot", page_icon="📘", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []


def render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander(f"Nguon tham khao ({len(sources)})"):
        for index, source in enumerate(sources, 1):
            metadata = source.get("metadata", {})
            st.markdown(
                f"**Document {index} - {metadata.get('title', 'Tai lieu')}**  "
                f"\nNguon: `{metadata.get('source', '')}`, "
                f"chunk: `{metadata.get('chunk_index', '')}`, "
                f"score: `{source.get('score', 0):.4f}`"
            )


with st.sidebar:
    st.title("Vat ly 10-12")
    st.caption("Tra cuu dua tren tai lieu vat ly da OCR")
    top_k = st.slider("So chunks", 3, 10, 5)
    if st.button("Xoa lich su"):
        st.session_state.messages = []
        st.rerun()

st.title("Chatbot RAG Vat ly 10-12")
st.caption("Hoi ve khai niem, dinh luat va cong thuc trong tai lieu lop 10, 11, 12.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        render_sources(message.get("sources", []))

query = st.chat_input("Nhap cau hoi vat ly...")
if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Dang tim tai lieu va tao cau tra loi..."):
            result = generate_with_citation(query, top_k=top_k)
        answer = result["answer"]
        sources = result.get("sources", [])
        st.markdown(answer)
        render_sources(sources)
    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
