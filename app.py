import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation, generate_with_mode


load_dotenv()

st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="",
    layout="wide",
)

# --- DEMO SEED: xoá khối này trước khi nộp bài, chỉ để demo trực quan ---
DEMO_QUESTIONS = [
    "Hộ kinh doanh có doanh thu bao nhiêu thì phải nộp thuế?",
    "Nghị quyết 198/2025/QH15 quy định thanh tra doanh nghiệp tối đa mấy lần một năm?",
    "Công thức tính đạo hàm của hàm số bậc hai là gì?",
]

if "messages" not in st.session_state:
    st.session_state.messages = []
    with st.spinner("Đang chuẩn bị demo..."):
        for demo_query in DEMO_QUESTIONS:
            demo_result = generate_with_citation(demo_query, top_k=5)
            st.session_state.messages.append({"role": "user", "content": demo_query})
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": demo_result["answer"],
                    "sources": demo_result["sources"],
                }
            )
# --- END DEMO SEED ---

with st.sidebar:
    st.title("RAG Chatbot")
    st.caption("Pháp luật cho hộ kinh doanh — chính sách, thuế, hóa đơn, thương mại điện tử")
    top_k = st.slider("Số chunks", 3, 10, 5)

    retrieval_mode = st.radio(
        "Chế độ retrieval",
        ["Hybrid (dense + BM25 + RRF)", "Dense-only"],
        help="So sánh 2 cấu hình retrieval cho cùng một câu hỏi.",
    )
    use_reranking = retrieval_mode.startswith("Hybrid")

    with st.expander("Vì sao điểm 2 chế độ khác nhau?"):
        st.markdown(
            "- **Dense** (embedding similarity) nắm ý nghĩa ngữ nghĩa tốt, nhưng có "
            "thể bỏ sót khi câu hỏi cần khớp chính xác số hiệu văn bản.\n"
            "- **BM25** khớp từ khóa chính xác (số nghị định, tên riêng) rất tốt, "
            "nhưng dễ bị nhiễu bởi từ ngữ hành chính lặp lại (\"quy định\", \"nội dung\"...) "
            "trong văn bản luật dài.\n"
            "- **RRF** gộp thứ hạng của cả hai, nên thường tốt hơn dense-only, nhưng "
            "đôi khi một kết quả nhiễu của BM25 vẫn có thể chen lên hạng cao và làm "
            "loãng kết quả dense đúng — xem chi tiết trong "
            "`group_project/evaluation/RESULT.md`."
        )


def render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander(f"Nguồn tham khảo ({len(sources)})"):
        for index, source in enumerate(sources, 1):
            metadata = source["metadata"]
            st.markdown(
                f"**[{index}] {metadata['title']}** — `{metadata['source']}` "
                f"(method: `{source['retrieval_method']}`, score: `{source['score']:.4f}`)"
            )
            st.caption(source["content"][:300] + ("…" if len(source["content"]) > 300 else ""))


st.title("RAG Chatbot")
st.caption("Hỏi đáp về pháp luật hộ kinh doanh — mỗi câu trả lời đều kèm nguồn trích dẫn")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources(message.get("sources", []))

query = st.chat_input("Nhập câu hỏi...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm và tổng hợp câu trả lời..."):
            result = generate_with_mode(query, top_k=top_k, use_reranking=use_reranking)
        answer = result["answer"]
        sources = result["sources"]
        st.markdown(answer)
        st.caption(f"Chế độ: `{retrieval_mode}`")
        render_sources(sources)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )
