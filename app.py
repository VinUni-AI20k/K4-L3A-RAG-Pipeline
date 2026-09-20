import streamlit as st
from dotenv import load_dotenv

from src.citations import format_citation
from src.task10_generation import generate_with_citation

load_dotenv()

st.set_page_config(
    page_title="Trợ Lý Pháp Luật: Pod & Chất Cấm | Team G36",
    page_icon="⚖️",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚖️ Trợ Lý Pháp Luật")
    st.subheader("Kiểm soát Pod & Chất cấm")
    st.markdown(
        """
        Hệ thống RAG hỗ trợ tra cứu pháp luật và cảnh báo về:
        - Quy định quản lý thuốc lá điện tử (**Pod, Vape**).
        - Nguy cơ pha trộn các chất ma túy tổng hợp (**Pod chill, cần sa tổng hợp**).
        - Khung xử phạt vi phạm hành chính & chế tài hình sự theo pháp luật Việt Nam.
        """
    )
    st.divider()

    st.markdown("### ⚙️ Cấu hình truy xuất")
    top_k = st.slider("Số lượng tài liệu trích xuất (top_k)", min_value=3, max_value=10, value=5, step=1)

    st.divider()
    st.info(
        "💡 **Lưu ý pháp lý:** Mọi thông tin phản hồi đều dựa trên tài liệu pháp luật và bài viết cảnh báo được thu thập. "
        "Hệ thống chỉ mang tính chất tham khảo, không thay thế văn bản quy phạm pháp luật chính thức hoặc tư vấn trực tiếp từ cơ quan chức năng."
    )

# --- MAIN CHAT UI ---
st.title("⚖️ Trợ Lý Pháp Luật: Thuốc Lá Điện Tử & Chất Cấm")
st.caption("Tra cứu văn bản pháp luật, căn cứ xử phạt và cảnh báo nguy cơ ma túy ngụy trang trong Pod")

def display_sources(sources: list[dict], retrieval_source: str = "hybrid") -> None:
    """Hiển thị danh sách nguồn tài liệu và căn cứ trích dẫn."""
    if not sources:
        return
    with st.expander(f"📚 Căn cứ pháp lý & Nguồn trích dẫn ({len(sources)} tài liệu | Retrieval: {retrieval_source})"):
        for index, item in enumerate(sources, 1):
            metadata = item.get("metadata", {})
            citation_title = format_citation(metadata)
            score = item.get("score", 0.0)
            url = metadata.get("url")

            st.markdown(f"**[E{index}] {citation_title}**")
            meta_info = f"*(Độ tương quan/Rank: `{score:.4f}` | Loại: `{metadata.get('doc_type', 'N/A')}`)*"
            if url:
                meta_info += f" — [Xem văn bản gốc]({url})"
            st.caption(meta_info)
            st.text_area(
                f"Trích đoạn nội dung [E{index}]",
                value=item.get("content", "").strip(),
                height=110,
                key=f"source_content_{index}_{item.get('id', '')}",
                disabled=True,
            )
            st.divider()

# Hiển thị lịch sử hội thoại
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("role") == "assistant" and msg.get("sources"):
            display_sources(msg["sources"], msg.get("retrieval_source", "hybrid"))

# Nhận câu hỏi từ người dùng
query = st.chat_input("Nhập câu hỏi (ví dụ: Hút pod chill chứa chất cấm bị xử lý thế nào?)...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tra cứu cơ sở pháp lý và đối soát điều luật..."):
            result = generate_with_citation(query, top_k=top_k)
            answer = result.get("answer", "Tôi không thể xác minh thông tin này từ nguồn hiện có.")
            sources = result.get("sources", [])
            retrieval_source = result.get("retrieval_source", "none")

            st.markdown(answer)
            if sources:
                display_sources(sources, retrieval_source)

    # Lưu phản hồi vào session state để giữ lịch sử hội thoại
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "retrieval_source": retrieval_source,
    })
