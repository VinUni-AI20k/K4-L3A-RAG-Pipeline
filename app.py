"""Vinhomes research assistant. Run: streamlit run app.py."""
import json
import time
from urllib.parse import urlparse

import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import SAFE_REFUSAL, generate_with_citation, reorder_for_llm

load_dotenv()
st.set_page_config(page_title="Vinhomes | Trợ lý thông tin", page_icon="🏙️", layout="wide")
st.markdown("""<style>
.stApp {
    --text-color: #14263d;
    --background-color: #f8fafc;
    --secondary-background-color: #e8eef6;
    --primary-color: #1d4ed8;
    background: #f8fafc;
    color: #14263d;
    color-scheme: light;
}
[data-testid="stHeader"], [data-testid="stBottom"] {background: #f8fafc;}
[data-testid="stSidebar"] {background: #e8eef6; color: #14263d;}
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],
[data-testid="stMetricLabel"], [data-testid="stMetricValue"],
[data-testid="stText"], [data-testid="stExpander"] summary {color: #14263d;}
[data-testid="stCaptionContainer"] p {color: #334155;}
[data-testid="stChatInput"], [data-testid="stChatInput"] textarea {
    background: #ffffff; color: #14263d; -webkit-text-fill-color: #14263d;
}
[data-testid="stChatInput"] textarea::placeholder {color: #52647a; -webkit-text-fill-color: #52647a;}
[data-testid="stChatInputSubmitButton"] {color: #1d4ed8; background: #e8eef6;}
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button,
[data-testid="stLinkButton"] a {background: #ffffff; color: #173b70; border: 1px solid #8da5c2;}
[data-testid="stButton"] button:hover {background: #e8eef6; border-color: #1d4ed8;}
[data-testid="stAlert"] {background: #e7efff; color: #173b70;}
.block-container {max-width: 1100px; padding-top: 2.5rem;}
[data-testid="stSidebar"] {border-right: 1px solid #b7c7da;}
[data-testid="stChatMessage"] {
    border: 1px solid #b7c7da;
    border-radius: 16px;
    background: var(--background-color);
    color: var(--text-color);
}
[data-testid="stCaptionContainer"] {
    color: var(--text-color);
    opacity: 0.85;
}
[data-testid="stChatInput"] {border: 1px solid #8da5c2; border-radius: 14px;}
[data-testid="stExpander"] {border-color: #b7c7da;}
[data-testid="stMarkdownContainer"] p {line-height: 1.7;}
h1,h2,h3 {letter-spacing: -0.025em; color: var(--text-color);}
</style>""", unsafe_allow_html=True)

METHODS = {"hybrid": "Hybrid · Dense + BM25 + RRF", "dense": "Dense · Ngữ nghĩa",
           "pageindex": "Fallback · PageIndex", "none": "Không đủ bằng chứng"}


def render_answer(message: dict) -> None:
    st.markdown(message["answer"])
    sources = message.get("sources", [])
    method = message.get("retrieval_source", "none")
    a, b, c = st.columns(3)
    a.metric("Phương thức tìm kiếm", {"hybrid": "Hybrid", "dense": "Dense", "pageindex": "Fallback"}.get(method, "—"))
    b.metric("Nguồn tham khảo", len(sources))
    c.metric("Thời gian phản hồi", f"{message.get('latency_s', 0):.1f} giây")
    if message.get("status") in {"provider_error", "retrieval_error"}:
        st.warning("Dịch vụ xử lý đang không khả dụng. Vui lòng thử lại sau.")
    if sources:
        best = max(float(source["score"]) for source in sources)
        st.caption(f"Score cao nhất: {best:.4f} · {METHODS.get(method, method)}")
        st.caption("Score phản ánh mức ưu tiên truy xuất, chưa phải xác suất câu trả lời đúng. "
                   "Dense dùng cosine; Hybrid dùng RRF; PageIndex dùng thứ tự trích dẫn.")
        for source in sorted(sources, key=lambda item: item.get("citation_id", 0)):
            meta = source["metadata"]
            number = source.get("citation_id", 1)
            with st.expander(f"[Document {number}] {meta['title']}"):
                st.caption(f"Score: {source['score']:.4f} · {source['retrieval_method']} · {meta['doc_type']}")
                if meta.get("page_number"):
                    st.caption(f"Trang {meta['page_number']} trong bản PDF chuẩn hóa")
                st.text(meta["source"])
                url = meta.get("url")
                if url and urlparse(url).scheme in {"http", "https"} and urlparse(url).netloc:
                    st.link_button("Mở nguồn tham khảo", url)
                st.markdown(source["content"])


if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("VINHOMES")
    st.caption("TRỢ LÝ THÔNG TIN & CHÍNH SÁCH")
    st.divider()
    st.markdown("**Hybrid · Dense + BM25 + RRF**")
    top_k = st.slider("Số đoạn tham khảo", 1, 10, 5)
    st.caption("Hybrid tự thử PageIndex khi kết quả ngữ nghĩa yếu và dịch vụ đã được cấu hình.")
    st.divider()
    st.markdown("**Phạm vi tài liệu**")
    st.write("5 bài tin dự án · 3 tài liệu chính sách")
    st.caption("Thông tin phản ánh thời điểm của từng tài liệu. Hãy nêu tên dự án và mốc thời gian khi hỏi về ưu đãi.")
    if st.button("Cuộc trò chuyện mới", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    if st.session_state.messages:
        st.download_button("Tải cuộc trò chuyện", json.dumps(st.session_state.messages, ensure_ascii=False, indent=2),
                           file_name="vinhomes-chat.json", mime="application/json", use_container_width=True)

st.title("Thông tin rõ ràng. Có nguồn đối chiếu.")
st.caption("Tra cứu dự án, chính sách bán hàng và quyền lợi khách hàng Vinhomes.")

example = None
if not st.session_state.messages:
    st.info("Mỗi câu trả lời có trích dẫn để bạn kiểm tra lại thông tin trong tài liệu.")
    cols = st.columns(3)
    prompts = ["Khách hàng gửi khiếu nại Vinhomes qua những kênh nào?",
               "Theo bài ngày 27/06/2025, Ocean Park 3 hỗ trợ vay bao nhiêu?",
               "Khách hàng có quyền chỉnh sửa thông tin cá nhân không?"]
    for col, label, prompt in zip(cols, ["Kênh khiếu nại", "Ưu đãi mua nhà", "Bảo vệ thông tin"], prompts):
        if col.button(label, use_container_width=True):
            example = prompt

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            render_answer(message)

query = st.chat_input("Nhập câu hỏi đầy đủ, tên dự án và mốc thời gian…", max_chars=2000) or example
if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    with st.chat_message("assistant"):
        started = time.perf_counter()
        with st.spinner("Đang tìm tài liệu và đối chiếu thông tin…"):
            try:
                answer = generate_with_citation(query, top_k=top_k)
                # Main returns sources in score order, while its prompt uses
                # reorder_for_llm. Map citation labels to that exact order.
                sources = answer.get("sources", [])
                labels = {item["id"]: number for number, item in enumerate(reorder_for_llm(sources), 1)}
                answer = {**answer, "sources": [
                    {**item, "citation_id": labels[item["id"]]} for item in sources
                ]}
            except Exception:
                answer = {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none", "status": "provider_error"}
        answer.update(role="assistant", latency_s=time.perf_counter() - started)
        render_answer(answer)
    st.session_state.messages.append(answer)
