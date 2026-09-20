"""Streamlit UI for the grounded Vietnam travel RAG assistant."""
from __future__ import annotations

import inspect
import os
import time
from datetime import datetime
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation
from src.task4_chunking_indexing import get_collection

load_dotenv()
st.set_page_config(page_title="Vietnam Travel RAG", page_icon="🧭", layout="wide")

# CSS tương thích hoàn hảo cho cả Light Mode và Dark Mode
st.markdown("""
<style>
/* Tự động đổi màu nền và màu chữ chung theo chế độ của Streamlit */
.stApp {
    background-color: var(--background-color);
    color: var(--text-color);
}
.block-container { 
    max-width: 980px; 
    padding-top: 2rem; 
    padding-bottom: 5rem; 
}

/* Sidebar styling tương thích Dark/Light mode */
[data-testid="stSidebar"] { 
    background-color: var(--secondary-background-color);
    border-right: 1px solid rgba(128, 128, 128, 0.2); 
}

/* Hero Banner dùng màu bán trong suốt hoặc biến đổi linh hoạt */
.hero { 
    padding: 1.35rem 1.5rem; 
    border: 1px solid rgba(73, 164, 135, 0.3); 
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(73, 164, 135, 0.05), rgba(73, 164, 135, 0.15)); 
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.05);
    margin-bottom: 1.25rem; 
}
.hero h1 { 
    margin: 0; 
    font-size: 2rem; 
}
.hero p { 
    margin: .45rem 0 0; 
    opacity: 0.8; 
}

/* Khung hiển thị trích dẫn nguồn */
.source-preview { 
    border-left: 3px solid #49a487; 
    padding: .15rem 0 .15rem .85rem; 
}

/* Chat Message khung bọc nội dung */
[data-testid="stChatMessage"] { 
    border: 1px solid rgba(128, 128, 128, 0.2); 
    border-radius: 14px;
    padding: .65rem .85rem; 
}
</style>
""", unsafe_allow_html=True)

SUGGESTED_QUESTIONS = (
    "Hà Giang mùa nào đẹp và cần chuẩn bị gì?",
    "Gợi ý lịch trình du lịch Đà Nẵng.",
    "Phú Quốc có những điểm tham quan nào nổi bật?",
    "Quy định nào cần lưu ý khi đi du lịch?",
)


def _supported_options() -> set[str]:
    """Inspect the loaded API so a stale Streamlit module cannot crash the UI."""
    parameters = inspect.signature(generate_with_citation).parameters
    if any(item.kind == inspect.Parameter.VAR_KEYWORD for item in parameters.values()):
        return {"top_k", "score_threshold", "use_reranking"}
    return set(parameters)


def run_generation(query: str, top_k: int, threshold: float,
                   reranking: bool) -> dict[str, Any]:
    requested = {
        "top_k": top_k,
        "score_threshold": threshold,
        "use_reranking": reranking,
    }
    supported = _supported_options()
    return generate_with_citation(
        query, **{key: value for key, value in requested.items() if key in supported}
    )


def show_sources(sources: list[dict[str, Any]], namespace: str) -> None:
    if not sources:
        st.info("Không có đoạn tài liệu nào được dùng cho câu trả lời này.")
        return
    st.markdown("#### Nguồn đã sử dụng")
    for index, source in enumerate(sources, 1):
        metadata = source.get("metadata", {})
        title = metadata.get("title") or metadata.get("source") or "Không rõ nguồn"
        method = source.get("retrieval_method", "unknown")
        score = source.get("score")
        score_text = f" · {float(score):.4f}" if isinstance(score, (int, float)) else ""
        with st.expander(f"[{index}] {title} · {method}{score_text}"):
            st.caption(
                f"{metadata.get('doc_type', 'document')} · "
                f"{metadata.get('source', 'Không rõ')} · chunk {metadata.get('chunk_index', '?')}"
            )
            url = metadata.get("url")
            if isinstance(url, str) and url.startswith(("http://", "https://")):
                st.link_button("Mở nguồn gốc ↗", url, key=f"source-{namespace}-{index}")
            content = str(source.get("content", "")).strip()
            preview = content if len(content) <= 1_500 else f"{content[:1_500].rstrip()}…"
            st.markdown("> " + preview.replace("\n", "\n> "))
            if len(content) > 1_500:
                with st.popover("Xem toàn bộ đoạn tài liệu"):
                    st.markdown(content)


def conversation_as_markdown(messages: list[dict[str, Any]]) -> str:
    lines = ["# Hội thoại Vietnam Travel RAG", ""]
    for message in messages:
        heading = "Người dùng" if message.get("role") == "user" else "Trợ lý"
        lines.extend((f"## {heading}", "", str(message.get("content", "")), ""))
        for index, source in enumerate(message.get("sources", []), 1):
            metadata = source.get("metadata", {})
            lines.append(f"- [{index}] {metadata.get('title', metadata.get('source', 'Nguồn'))}")
        lines.append("")
    return "\n".join(lines)


if "messages" not in st.session_state:
    st.session_state.messages = []

supported_options = _supported_options()
advanced_ready = {"score_threshold", "use_reranking"}.issubset(supported_options)

with st.sidebar:
    st.title("🧭 Vietnam Travel RAG")
    st.caption("Trợ lý hỏi đáp có truy xuất và dẫn nguồn từ kho tri thức của dự án.")
    st.subheader("Trạng thái hệ thống")
    chunk_count = 0
    try:
        chunk_count = get_collection().count()
    except Exception as exc:
        st.error(f"Không mở được vector index: {exc}")
    else:
        if chunk_count:
            st.success(f"Vector index sẵn sàng · {chunk_count:,} chunks")
        else:
            st.warning("Vector index đang trống. Hãy chạy Task 4 trước.")
    st.caption(f"Model: `{os.getenv('LLM_MODEL', 'gemini-3.5-flash-lite')}`")
    if not advanced_ready:
        st.warning("Backend đang dùng API cũ. App vẫn chạy; hãy khởi động lại Streamlit để nạp API mới.")

    with st.expander("⚙️ Tùy chỉnh retrieval"):
        top_k = st.slider("Số đoạn ngữ cảnh", 1, 10, 5)
        score_threshold = st.slider(
            "Ngưỡng fallback", 0.0, 1.0, 0.82, 0.02, disabled=not advanced_ready,
            help="Dense score thấp hơn ngưỡng sẽ kích hoạt PageIndex fallback.",
        )
        use_reranking = st.toggle(
            "RRF reranking", value=True, disabled=not advanced_ready,
            help="Kết hợp kết quả dense và BM25 bằng Reciprocal Rank Fusion.",
        )
    left, right = st.columns(2)
    with left:
        if st.button("Xóa chat", use_container_width=True, disabled=not st.session_state.messages):
            st.session_state.messages = []
            st.rerun()
    with right:
        st.download_button(
            "Tải chat", conversation_as_markdown(st.session_state.messages),
            file_name=f"rag-chat-{datetime.now():%Y%m%d-%H%M}.md",
            mime="text/markdown", use_container_width=True,
            disabled=not st.session_state.messages,
        )

st.markdown("""
<div class="hero"><h1>Trợ lý Du lịch Việt Nam</h1>
<p>Hỏi đáp từ corpus nội bộ · Hybrid retrieval · Câu trả lời có nguồn kiểm chứng</p></div>
""", unsafe_allow_html=True)

if not st.session_state.messages:
    st.markdown("##### Bạn có thể bắt đầu với")
    columns = st.columns(2)
    for index, suggestion in enumerate(SUGGESTED_QUESTIONS):
        with columns[index % 2]:
            if st.button(
                suggestion,
                key=f"suggestion-{index}",
                use_container_width=True,
                disabled=not bool(chunk_count),
            ):
                st.session_state.pending_query = suggestion

for message_index, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            details = (
                f"Retrieval: **{message.get('retrieval_source', 'none')}** · "
                f"{len(message.get('sources', []))} nguồn"
            )
            if isinstance(message.get("latency"), (int, float)):
                details += f" · {message['latency']:.1f}s"
            st.caption(details)
            show_sources(message.get("sources", []), f"history-{message_index}")

typed_query = st.chat_input("Ví dụ: Hà Giang mùa nào đẹp?", disabled=not bool(chunk_count))
query = typed_query or st.session_state.pop("pending_query", None)

if query and query.strip():
    query = query.strip()
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    with st.chat_message("assistant"):
        started_at = time.perf_counter()
        try:
            with st.spinner("Đang tìm kiếm và kiểm chứng nguồn…"):
                result = run_generation(query, top_k, score_threshold, use_reranking)
        except Exception as exc:
            st.error(f"Không thể xử lý câu hỏi: {exc}")
            st.caption("Hãy kiểm tra GEMINI_API_KEY, vector index và khởi động lại Streamlit.")
        else:
            latency = time.perf_counter() - started_at
            answer = result.get("answer", "Không nhận được câu trả lời.")
            sources = result.sources if hasattr(result, 'sources') else result.get("sources", [])
            retrieval_source = result.get("retrieval_source", "none")
            st.markdown(answer)
            st.caption(f"Retrieval: **{retrieval_source}** · {len(sources)} nguồn · {latency:.1f}s")
            show_sources(sources, f"current-{len(st.session_state.messages)}")
            st.session_state.messages.append({
                "role": "assistant", "content": answer, "sources": sources,
                "retrieval_source": retrieval_source, "latency": latency,
            })