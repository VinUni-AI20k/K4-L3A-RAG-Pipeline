import re

import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation, generate_with_history

CITATION_COLORS = ["#c9a24b", "#2f6fa8", "#2f7a4f", "#a8452f", "#7a4fa8", "#4f8ba8", "#a8792f", "#5a7a2f"]


def highlight_citations(text: str) -> str:
    """Bọc [Document N] bằng badge màu, khớp màu với danh sách nguồn bên dưới."""
    def repl(match: "re.Match[str]") -> str:
        n = int(match.group(1))
        color = CITATION_COLORS[(n - 1) % len(CITATION_COLORS)]
        return (
            f'<span style="background:{color}22;color:{color};border:1px solid {color};'
            f'border-radius:6px;padding:1px 7px;font-weight:600;font-size:0.85em;">[{n}]</span>'
        )
    return re.sub(r"\[Document (\d+)\]", repl, text)


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
            color = CITATION_COLORS[(index - 1) % len(CITATION_COLORS)]
            st.markdown(
                f'<span style="background:{color}22;color:{color};border:1px solid {color};'
                f'border-radius:6px;padding:1px 7px;font-weight:600;font-size:0.85em;">[{index}]</span>'
                f" **{metadata['title']}** — `{metadata['source']}` "
                f"(method: `{source['retrieval_method']}`, score: `{source['score']:.4f}`)",
                unsafe_allow_html=True,
            )
            st.caption(source["content"][:300] + ("…" if len(source["content"]) > 300 else ""))


st.title("RAG Chatbot")
st.caption("Hỏi đáp về pháp luật hộ kinh doanh — mỗi câu trả lời đều kèm nguồn trích dẫn")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.markdown(highlight_citations(message["content"]), unsafe_allow_html=True)
            render_sources(message.get("sources", []))
        else:
            st.markdown(message["content"])

query = st.chat_input("Nhập câu hỏi...")

if query:
    # Lịch sử trước khi thêm câu hỏi mới — dùng để viết lại câu hỏi follow-up
    # thành câu hỏi độc lập (bonus: conversation memory).
    history = [
        {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
    ]
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm và tổng hợp câu trả lời..."):
            result = generate_with_history(
                query, history=history, top_k=top_k, use_reranking=use_reranking
            )
        answer = result["answer"]
        sources = result["sources"]
        st.markdown(highlight_citations(answer), unsafe_allow_html=True)
        standalone_query = result.get("standalone_query")
        if standalone_query and standalone_query.strip() != query.strip():
            st.caption(f"🧠 Hiểu câu hỏi (dựa vào lịch sử) là: *{standalone_query}*")
        st.caption(f"Chế độ: `{retrieval_mode}`")
        render_sources(sources)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )
