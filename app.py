import streamlit as st
from dotenv import load_dotenv

from src.task9_retrieval_pipeline import RERANKER_ENABLED
from src.task10_generation import generate_with_citation
from src.task13_conversation_memory import answer_with_memory
from src.ui_citations import highlight_evidence, number_citations, order_sources


load_dotenv()

st.set_page_config(
    page_title="RAG Chatbot",
    layout="wide",
)


def render_answer(answer: str, sources: list[dict]) -> list[str]:
    """Hiện câu trả lời với citation dạng badge số; trả về chunk ID theo số."""
    answer_html, cited_ids = number_citations(answer, sources)
    st.markdown(answer_html, unsafe_allow_html=True)
    return cited_ids


def show_sources(sources: list[dict], retrieval_source: str, answer: str = "", cited_ids: list[str] | None = None) -> None:
    """Nguồn được cite lên trước, đánh số khớp badge, highlight câu bằng chứng."""
    if not sources:
        return
    cited_ids = cited_ids or []

    with st.expander(f"Nguồn tham khảo ({len(cited_ids)} được cite / {len(sources)} lấy về)"):
        st.caption(f"Nguồn truy hồi: {retrieval_source}")
        for number, source in order_sources(sources, cited_ids):
            metadata = source["metadata"]
            if number is not None:
                st.markdown(
                    f'<span style="display:inline-block;padding:0 8px;border-radius:8px;'
                    f'background:#1f77b4;color:#fff;font-weight:600">{number}</span> '
                    f"**{metadata['title']}**",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"<span style='opacity:0.6'>◦ {metadata['title']} — lấy về nhưng không được cite</span>", unsafe_allow_html=True)
            st.caption(
                f"Citation: [{source['id']}] · Tệp: {metadata['source']} · "
                f"Phương thức: {source['retrieval_method']} · "
                f"Điểm truy hồi: {source['score']:.4f}"
            )
            if metadata.get("url"):
                st.write(metadata["url"])
            if number is not None:
                body = highlight_evidence(source["content"], answer)
                st.markdown(
                    f'<div style="border-left:4px solid #1f77b4;padding-left:10px">{body}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"<div style='opacity:0.6'>{highlight_evidence(source['content'], '')}</div>", unsafe_allow_html=True)
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
        if message["role"] == "assistant":
            cited = render_answer(message["content"], message.get("sources", []))
            if message.get("standalone_query"):
                st.caption(f"Câu hỏi đã diễn giải: {message['standalone_query']}")
            show_sources(
                message.get("sources", []),
                message.get("retrieval_source", "none"),
                message["content"],
                cited,
            )
        else:
            st.markdown(message["content"])

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
        cited = render_answer(result["answer"], result["sources"])
        show_sources(result["sources"], result["retrieval_source"], result["answer"], cited)

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
        "retrieval_source": result["retrieval_source"],
        "standalone_query": standalone,
    })
