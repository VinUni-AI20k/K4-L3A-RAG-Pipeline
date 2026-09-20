import streamlit as st
from dotenv import load_dotenv
from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="Hỏi đáp Thư viện Trung tâm ĐHQG-HCM",
    page_icon="📚",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("📚 Thư Viện TVTT RAG")
    st.markdown(
        "**Hệ thống tra cứu thông tin & quy định:**\n"
        "- Chính sách mượn trả tài liệu TVTT (TB 52/TB-TVTT).\n"
        "- Biểu phí dịch vụ và tiền thế chân (TB 106/TB-TVTT).\n"
        "- Hướng dẫn tra cứu mục lục trực tuyến (Phòng PVĐG).\n"
    )
    st.divider()
    top_k = st.slider("Số lượng chunks tham khảo (top_k)", min_value=1, max_value=10, value=5)
    st.caption("Cấu hình pipeline: Hybrid Retrieval (Dense Semantic + Lexical BM25) kết hợp RRF Reranking và Fallback.")
    
    if st.button("Xóa lịch sử chat"):
        st.session_state.messages = []
        st.rerun()

st.title("Trợ lý Thông tin Thư viện Trung tâm ĐHQG-HCM")
st.caption("Đặt câu hỏi về quy định mượn trả, gia hạn sách, tiền thế chân, làm thẻ thư viện hoặc phí phạt...")

# Render lịch sử hội thoại
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        sources = message.get("sources", [])
        if sources:
            retrieval_source = message.get("retrieval_source", "hybrid")
            with st.expander(f"📌 Nguồn tham khảo ({len(sources)} tài liệu | Phương thức: {retrieval_source})"):
                for idx, src in enumerate(sources, 1):
                    meta = src.get("metadata", {})
                    title = meta.get("title", "Tài liệu")
                    source_file = meta.get("source", "")
                    score = src.get("score", 0.0)
                    method = src.get("retrieval_method", "")
                    st.markdown(f"**[{idx}] {title}** — *Điểm: `{score:.4f}` ({method})*")
                    if meta.get("url"):
                        st.markdown(f"🔗 [Liên kết nguồn]({meta['url']}) | File: `{source_file}`")
                    else:
                        st.caption(f"Tập tin: `{source_file}`")
                    st.text(src.get("content", "")[:300] + ("..." if len(src.get("content", "")) > 300 else ""))

query = st.chat_input("Nhập câu hỏi của bạn (ví dụ: Phí phạt trễ hạn mượn sách là bao nhiêu?)...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm tài liệu và tổng hợp câu trả lời..."):
            result = generate_with_citation(query, top_k=top_k)
            answer = result["answer"]
            sources = result.get("sources", [])
            retrieval_source = result.get("retrieval_source", "hybrid")
            st.markdown(answer)

            if sources:
                with st.expander(f"📌 Nguồn tham khảo ({len(sources)} tài liệu | Phương thức: {retrieval_source})"):
                    for idx, src in enumerate(sources, 1):
                        meta = src.get("metadata", {})
                        title = meta.get("title", "Tài liệu")
                        source_file = meta.get("source", "")
                        score = src.get("score", 0.0)
                        method = src.get("retrieval_method", "")
                        st.markdown(f"**[{idx}] {title}** — *Điểm: `{score:.4f}` ({method})*")
                        if meta.get("url"):
                            st.markdown(f"🔗 [Liên kết nguồn]({meta['url']}) | File: `{source_file}`")
                        else:
                            st.caption(f"Tập tin: `{source_file}`")
                        st.text(src.get("content", "")[:300] + ("..." if len(src.get("content", "")) > 300 else ""))

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "retrieval_source": retrieval_source,
    })
