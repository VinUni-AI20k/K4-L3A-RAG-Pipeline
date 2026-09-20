import streamlit as st
from dotenv import load_dotenv


load_dotenv()

st.set_page_config(
    page_title="Vinhomes Knowledge Chat",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { max-width: 1180px; padding-top: 2rem; }
    .app-kicker { color: #b45f06; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; }
    .app-title { color: #183b56; font-size: 2.4rem; font-weight: 750; line-height: 1.1; margin: 0.25rem 0 0.5rem; }
    .app-subtitle { color: #52606d; margin-bottom: 1.5rem; }
    .source-card { border-left: 3px solid #d98b2b; background: #fffaf2; padding: 0.7rem 0.9rem; margin: 0.45rem 0; }
    .source-title { color: #183b56; font-weight: 700; }
    .source-meta { color: #66788a; font-size: 0.82rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."


def _method_label(method: str) -> str:
    labels = {
        "hybrid": "Hybrid + RRF",
        "dense": "Dense search",
        "pageindex": "Fallback theo trang",
        "none": "Không có nguồn",
    }
    return labels.get(method, method or "Không xác định")


def _score_percent(score: object) -> float:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return 0.0
    # Dense scores are commonly in [0, 1], while RRF/BM25 may use another scale.
    if value <= 1:
        return max(0.0, min(value * 100, 100.0))
    return max(0.0, min(value * 100 / (value + 1), 100.0))


def _render_sources(sources: list[dict]) -> None:
    if not sources:
        st.caption("Chưa có nguồn nào được trả về.")
        return

    st.markdown("#### Citation và nguồn tham khảo")
    for index, source in enumerate(sources, start=1):
        metadata = source.get("metadata") or {}
        title = metadata.get("title") or metadata.get("source") or f"Nguồn {index}"
        source_name = metadata.get("source") or "Không rõ file"
        method = _method_label(str(source.get("retrieval_method", "")))
        score = source.get("score", 0.0)
        with st.container(border=True):
            st.markdown(
                f"**[{index}] {title}**  \n"
                f"`{source_name}` · {method} · Score: `{float(score):.4f}`"
            )
            with st.expander("Xem đoạn trích"):
                st.write(source.get("content", ""))


def _render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] != "assistant":
            return

        method = message.get("retrieval_source", "none")
        sources = message.get("sources", [])
        scores = [float(item.get("score", 0.0)) for item in sources if item.get("score") is not None]
        metric_columns = st.columns(2)
        metric_columns[0].metric("Phương thức", _method_label(method))
        metric_columns[1].metric("Score cao nhất", f"{max(scores):.4f}" if scores else "N/A")
        _render_sources(sources)


if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.markdown("## Vinhomes RAG")
    st.caption("Tra cứu thông tin từ bộ tài liệu pháp lý và tin tức của nhóm.")
    top_k = st.slider("Số nguồn truy hồi", min_value=3, max_value=10, value=5)
    st.divider()
    st.markdown("**Retrieval**")
    st.caption("Hybrid + RRF, dense search và fallback theo trang được quyết định bởi pipeline.")
    if st.button("Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.markdown('<div class="app-kicker">Knowledge assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="app-title">Hỏi đáp Vinhomes</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Câu trả lời được tạo từ nguồn đã thu thập và hiển thị kèm citation để kiểm chứng.</div>',
    unsafe_allow_html=True,
)

for message in st.session_state.messages:
    _render_message(message)

query = st.chat_input("Hỏi về chính sách, khiếu nại, mở bán hoặc khuyến mại...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm nguồn và tổng hợp câu trả lời..."):
            try:
                from src.task10_generation import generate_with_citation

                result = generate_with_citation(query, top_k=top_k)
                answer = result.get("answer") or SAFE_REFUSAL
                sources = result.get("sources") or []
                retrieval_source = result.get("retrieval_source", "none")
            except Exception as error:
                answer = SAFE_REFUSAL
                sources = []
                retrieval_source = "none"
                st.warning(f"Pipeline chưa sẵn sàng: {error}")

        st.markdown(answer)
        scores = [float(item.get("score", 0.0)) for item in sources if item.get("score") is not None]
        metric_columns = st.columns(2)
        metric_columns[0].metric("Phương thức", _method_label(retrieval_source))
        metric_columns[1].metric("Score cao nhất", f"{max(scores):.4f}" if scores else "N/A")
        _render_sources(sources)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "sources": sources,
                "retrieval_source": retrieval_source,
            }
        )
