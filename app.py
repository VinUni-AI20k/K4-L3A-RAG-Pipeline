import html
import re

import streamlit as st
from dotenv import load_dotenv


load_dotenv()

st.set_page_config(
    page_title="Shopee Policy Assistant",
    page_icon="🛒",
    layout="wide",
)

EXAMPLE_QUESTIONS = [
    "Người mua có bao nhiêu ngày để gửi yêu cầu trả hàng/hoàn tiền?",
    "Thanh toán bằng thẻ tín dụng thì bao lâu nhận được tiền hoàn?",
    "Shopee giải quyết tranh chấp không phải trả hàng/hoàn tiền trong bao lâu?",
    "Thời tiết Hà Nội hôm nay thế nào?",
]

if "messages" not in st.session_state:
    st.session_state.messages = []


@st.cache_resource(show_spinner="Đang nạp embedding model và index...")
def load_pipeline():
    from src.task10_generation import LLM_MODEL, LLM_PROVIDER, generate_answer
    from src.task4_chunking_indexing import get_collection
    from src.task9_retrieval_pipeline import SCORE_THRESHOLD

    chunk_count = get_collection().count()
    return generate_answer, chunk_count, f"{LLM_PROVIDER}/{LLM_MODEL}", SCORE_THRESHOLD


def highlight_citations(answer: str) -> str:
    """Tô đậm các citation [n] để dễ đối chiếu với danh sách nguồn."""
    return re.sub(r"\[(\d+)\]", r"**[\1]**", answer)


def render_sources(sources: list[dict], answer: str) -> None:
    if not sources:
        st.caption("Không có nguồn nào được dùng (safe refusal).")
        return
    cited = {int(number) for number in re.findall(r"\[(\d+)\]", answer)}
    with st.expander(f"Nguồn ({len(sources)}) — đã trích dẫn: {sorted(cited) or 'không'}"):
        for number, source in enumerate(sources, 1):
            metadata = source["metadata"]
            marker = "✅" if number in cited else "▫️"
            url = metadata.get("url")
            title = f"[{metadata['title']}]({url})" if url else metadata["title"]
            st.markdown(
                f"{marker} **[{number}]** {title}  \n"
                f"`{source['retrieval_method']}` · score `{source['score']:.4f}` · "
                f"{metadata['doc_type']} · {metadata['source']} · chunk {metadata['chunk_index']}"
            )
            st.markdown(
                "<div style='font-size:0.85em;opacity:0.8;border-left:3px solid #ee4d2d;"
                "padding-left:8px;margin-bottom:12px;white-space:pre-wrap'>"
                f"{html.escape(source['content'])}</div>",
                unsafe_allow_html=True,
            )


generate_answer, chunk_count, model_label, threshold = load_pipeline()

with st.sidebar:
    st.title("🛒 Shopee Policy Assistant")
    st.caption(
        "Hỏi đáp về chính sách trả hàng/hoàn tiền, vận chuyển, đăng bán, "
        "hàng cấm và giải quyết tranh chấp trên Shopee Việt Nam."
    )
    top_k = st.slider("Số chunks", 3, 10, 5)
    use_hybrid = st.toggle("Hybrid (dense + BM25 + RRF)", value=True, help="Tắt = dense-only")
    st.divider()
    st.caption(f"Index: {chunk_count} chunks · LLM: {model_label} · fallback threshold: {threshold:.2f}")
    if st.button("Xoá hội thoại"):
        st.session_state.messages = []
        st.rerun()

st.title("Trợ lý chính sách Shopee")
st.caption(
    "Câu trả lời chỉ dựa trên tài liệu chính sách công khai tại help.shopee.vn, "
    "kèm citation [n] trỏ tới nguồn bên dưới. Ví dụ:"
)
columns = st.columns(len(EXAMPLE_QUESTIONS))
clicked = None
for column, question in zip(columns, EXAMPLE_QUESTIONS):
    if column.button(question, use_container_width=True):
        clicked = question

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            st.caption(f"retrieval_source: `{message['retrieval_source']}`")
            render_sources(message["sources"], message["content"])

query = st.chat_input("Nhập câu hỏi...") or clicked

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm nguồn và soạn câu trả lời..."):
            try:
                result = generate_answer(query, top_k=top_k, use_reranking=use_hybrid)
            except Exception as error:
                result = {
                    "answer": f"Đã xảy ra lỗi khi xử lý câu hỏi: {error}",
                    "sources": [],
                    "retrieval_source": "none",
                }
        answer = highlight_citations(result["answer"])
        st.markdown(answer)
        st.caption(f"retrieval_source: `{result['retrieval_source']}`")
        render_sources(result["sources"], answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": result["sources"],
        "retrieval_source": result["retrieval_source"],
    })
