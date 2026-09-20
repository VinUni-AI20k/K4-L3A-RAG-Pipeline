"""Streamlit chat UI for the Vietnam travel RAG assistant."""
import streamlit as st
from dotenv import load_dotenv
from src.task10_generation import generate_with_citation
from src.task4_chunking_indexing import get_collection

load_dotenv()
st.set_page_config(page_title="Vietnam Travel RAG", page_icon="🧭", layout="wide")

def show_sources(sources: list[dict]) -> None:
    if not sources:
        return
    st.markdown("#### Nguồn đã dùng")
    for index, source in enumerate(sources, 1):
        meta = source["metadata"]
        label = f"[{index}] {meta['title']} · {source['retrieval_method']} · Score: {source['score']:.4f}"
        with st.expander(label):
            if meta.get("url"):
                st.link_button("Mở nguồn gốc", meta["url"])
            st.caption(f"File: {meta['source']} · Chunk index: {meta.get('chunk_index', '?')}")
            st.markdown(source["content"])

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("🧭 Vietnam Travel RAG")
    st.caption("Hỏi về Hà Giang, Đà Nẵng, Phú Quốc, Tà Xùa, Nha Trang và quy định du lịch.")
    
    st.divider()
    st.subheader("⚙️ Thống số & Tham số Tìm kiếm")
    
    top_k = st.slider(
        "Số đoạn ngữ cảnh (top_k)",
        min_value=1,
        max_value=10,
        value=5,
        help="Số lượng đoạn văn bản tốt nhất gửi đến LLM để tổng hợp câu trả lời."
    )
    
    score_threshold = st.slider(
        "Ngưỡng Cosine Fallback (threshold)",
        min_value=0.0,
        max_value=1.0,
        value=0.82,
        step=0.02,
        help="Nếu điểm Cosine similarity của kết quả Dense < threshold, hệ thống tự động fallback sang PageIndex Vectorless Search."
    )
    
    use_reranking = st.toggle(
        "Kích hoạt RRF Reranking",
        value=True,
        help="Gộp và xếp hạng lại thứ tự giữa Dense Search và BM25 Search bằng công thức Reciprocal Rank Fusion (k=60)."
    )
    
    st.divider()
    st.caption("📊 Trạng thái Vector DB")
    try:
        chunk_count = get_collection().count()
        if chunk_count:
            st.success(f"Vector Index: {chunk_count} chunks")
        else:
            st.warning("Chưa có index. Chạy Task 4 trước.")
    except Exception as exc:
        st.error(f"Không mở được vector index: {exc}")

    if st.button("🗑️ Xóa hội thoại", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("Trợ lý Du lịch Việt Nam")
st.caption("Câu trả lời chỉ dựa trên corpus và luôn kèm nguồn có thể kiểm chứng.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            if "retrieval_source" in message:
                st.caption(f"Phương thức Retrieval: **{message['retrieval_source']}**")
            show_sources(message.get("sources", []))

if query := st.chat_input("Ví dụ: Hà Giang mùa nào đẹp?"):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    with st.chat_message("assistant"):
        with st.spinner("Đang tìm và kiểm chứng nguồn..."):
            result = generate_with_citation(
                query,
                top_k=top_k,
                score_threshold=score_threshold,
                use_reranking=use_reranking
            )
        st.markdown(result["answer"])
        st.caption(f"Phương thức Retrieval: **{result['retrieval_source']}**")
        show_sources(result["sources"])
    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
        "retrieval_source": result["retrieval_source"]
    })
