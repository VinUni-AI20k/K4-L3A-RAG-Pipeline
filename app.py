import uuid
import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="Trợ lý Quy chế & Dịch vụ Sinh viên VNU-UET",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Classical Editorial Design System Tokens from Chatbot.html
# ---------------------------------------------------------
CLASSICAL_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600&family=Lora:ital,wght@0,400;0,500;0,600;1,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">

<style>
/* CSS Variables directly aligned with Chatbot.html */
:root {
  --color-bg: #f3f2f2;
  --color-surface: #ffffff;
  --color-text: #201f1d;
  --color-accent: #b68235;
  --color-accent-hover: #a06f24;
  --color-divider: rgba(32, 31, 29, 0.15);
  --color-muted: rgba(32, 31, 29, 0.55);
  --font-heading: 'Cormorant Garamond', Georgia, serif;
  --font-body: 'Lora', Georgia, serif;
  --font-ui: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Force light warm background across ALL Streamlit containers - No Black Bars! */
html, body, .stApp, 
[data-testid="stAppViewContainer"], 
[data-testid="stAppViewBlockContainer"], 
[data-testid="stHeader"],
[data-testid="stToolbar"],
header,
footer,
.main,
div[data-testid="stBottom"],
.stBottom {
  background-color: #f3f2f2 !important;
  color: #201f1d !important;
  font-family: var(--font-body) !important;
}

/* Header bar styling */
header[data-testid="stHeader"] {
  background-color: #f3f2f2 !important;
  border-bottom: 1px solid var(--color-divider) !important;
}

header[data-testid="stHeader"] * {
  color: var(--color-text) !important;
}

/* Bottom Chat Input Fixed Container - eliminate dark bar */
div[data-testid="stBottom"],
.stBottom,
div[data-testid="stBottom"] > div {
  background-color: #f3f2f2 !important;
}

div[data-testid="stChatInput"] {
  background-color: transparent !important;
}

div[data-testid="stChatInput"] > div {
  background-color: #ffffff !important;
  border: 1px solid var(--color-divider) !important;
  border-radius: 6px !important;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
}

div[data-testid="stChatInput"] textarea {
  color: #201f1d !important;
  background-color: #ffffff !important;
  font-family: var(--font-body) !important;
  font-size: 14.5px !important;
}

div[data-testid="stChatInput"] textarea::placeholder {
  color: rgba(32, 31, 29, 0.45) !important;
}

div[data-testid="stChatInput"] button {
  color: var(--color-accent) !important;
  border: none !important;
}

/* Sidebar Styling */
section[data-testid="stSidebar"] {
  background-color: #edecec !important;
  border-right: 1px solid var(--color-divider) !important;
  padding-top: 1rem !important;
}

section[data-testid="stSidebar"] hr {
  margin: 0.8rem 0 !important;
  border-color: var(--color-divider) !important;
}

/* Typography Overrides */
h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-heading) !important;
  color: var(--color-text) !important;
  letter-spacing: -0.015em !important;
}

/* Custom classical button styles */
.stButton > button {
  font-family: var(--font-heading) !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  color: var(--color-text) !important;
  border: 1px solid var(--color-divider) !important;
  border-radius: 4px !important;
  background-color: #ffffff !important;
  transition: all 0.15s ease !important;
  padding: 0.35rem 0.75rem !important;
}

.stButton > button:hover {
  background-color: rgba(182, 130, 53, 0.08) !important;
  border-color: var(--color-accent) !important;
  color: var(--color-accent) !important;
}

/* Chat Message Cards */
.user-msg-card {
  background: #ffffff;
  border: 1px solid var(--color-divider);
  border-radius: 4px;
  padding: 12px 18px;
  max-width: 82%;
  margin-left: auto;
  margin-bottom: 18px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}

.user-msg-label {
  font-family: var(--font-ui);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-muted);
  margin-bottom: 4px;
}

.bot-msg-card {
  margin-bottom: 24px;
  padding-right: 20px;
}

.bot-msg-label {
  font-family: var(--font-ui);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-accent);
  font-weight: 600;
  margin-bottom: 6px;
}

.bot-msg-body {
  font-family: var(--font-body);
  font-size: 15px;
  line-height: 1.7;
  color: var(--color-text);
  text-align: justify;
}

.citation-box {
  border-left: 3px solid var(--color-accent);
  background: rgba(182, 130, 53, 0.05);
  padding: 8px 14px;
  margin-top: 12px;
  margin-bottom: 10px;
  border-radius: 0 4px 4px 0;
}

.citation-label {
  font-family: var(--font-ui);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-muted);
  margin-bottom: 4px;
  font-weight: 600;
}

/* Sidebar History Section Labels */
.sidebar-section-title {
  font-family: var(--font-ui);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-muted);
  margin-top: 12px;
  margin-bottom: 6px;
  font-weight: 600;
}

.badge-tag {
  display: inline-block;
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 3px;
  background: rgba(182, 130, 53, 0.14);
  color: #7d5411;
  border: 1px solid rgba(182, 130, 53, 0.3);
}

.disclaimer-text {
  font-family: var(--font-ui);
  font-size: 11px;
  color: var(--color-muted);
  text-align: center;
  margin-top: 8px;
  margin-bottom: 12px;
}
</style>
"""

st.markdown(CLASSICAL_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------
# Session State Initialization (Dynamic Real Chat History)
# ---------------------------------------------------------
# Mỗi session lưu: {"id": str, "title": str, "messages": list}
if "sessions" not in st.session_state:
    st.session_state.sessions = []

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None


def create_new_chat():
    """Tạo phiên hội thoại mới và lưu phiên hiện tại nếu có tin nhắn."""
    save_current_session()
    new_id = str(uuid.uuid4())
    st.session_state.current_session_id = new_id
    st.session_state.messages = []
    st.session_state.pending_query = None


def save_current_session():
    """Lưu trữ phiên hội thoại hiện tại vào danh sách lịch sử."""
    if not st.session_state.messages:
        return
    cur_id = st.session_state.current_session_id
    # Đặt tiêu đề là nội dung câu hỏi đầu tiên của người dùng
    title = "Hội thoại mới"
    for m in st.session_state.messages:
        if m["role"] == "user":
            title = m["content"].strip()
            if len(title) > 36:
                title = title[:33] + "..."
            break

    # Cập nhật nếu đã tồn tại, hoặc thêm mới
    found = False
    for s in st.session_state.sessions:
        if s["id"] == cur_id:
            s["title"] = title
            s["messages"] = list(st.session_state.messages)
            found = True
            break
    if not found:
        st.session_state.sessions.insert(0, {
            "id": cur_id,
            "title": title,
            "messages": list(st.session_state.messages),
        })


def load_session(session_id: str):
    """Nạp lại một hội thoại từ lịch sử."""
    save_current_session()
    for s in st.session_state.sessions:
        if s["id"] == session_id:
            st.session_state.current_session_id = s["id"]
            st.session_state.messages = list(s["messages"])
            st.session_state.pending_query = None
            st.rerun()


def trigger_query(text: str):
    """Kích hoạt câu hỏi ngay lập tức từ chip gợi ý."""
    st.session_state.pending_query = text
    st.rerun()


# ---------------------------------------------------------
# Sidebar Component (Replicating Chatbot.html <aside>)
# ---------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="margin-bottom: 14px;">
          <div style="font-family: 'Cormorant Garamond', serif; font-size: 23px; font-weight: 700; color: #201f1d; line-height: 1.15;">Trợ lý Quy chế</div>
          <div style="font-family: 'Inter', sans-serif; font-size: 10.5px; letter-spacing: .12em; text-transform: uppercase; color: #b68235; font-weight: 600; margin-top: 4px;">Phòng Đào tạo · VNU-UET</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Nút Hội thoại mới
    if st.button("＋  Hội thoại mới", key="btn_new_chat", use_container_width=True):
        create_new_chat()
        st.rerun()

    st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid rgba(32, 31, 29, 0.15);'>", unsafe_allow_html=True)

    # Lịch sử hội thoại động thực tế (Chỉ hiển thị các hội thoại bạn đã chat)
    st.markdown("<div class='sidebar-section-title'>Lịch sử hội thoại của bạn</div>", unsafe_allow_html=True)
    
    # Đồng bộ session hiện tại vào danh sách để cập nhật sidebar ngay
    save_current_session()

    if not st.session_state.sessions:
        st.markdown(
            """
            <div style="font-family: 'Inter', sans-serif; font-size: 12px; color: rgba(32, 31, 29, 0.48); font-style: italic; padding: 6px 0; line-height: 1.5;">
              Chưa có hội thoại nào.<br>Lịch sử sẽ tự động lưu khi bạn bắt đầu trò chuyện.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for idx, s in enumerate(st.session_state.sessions):
            is_active = s["id"] == st.session_state.current_session_id
            prefix = "💬 " if not is_active else "👉 "
            btn_label = f"{prefix}{s['title']}"
            if st.button(btn_label, key=f"sess_btn_{s['id']}_{idx}", use_container_width=True):
                load_session(s["id"])

        if st.button("🗑️ Xóa toàn bộ lịch sử", key="btn_clear_all_history", use_container_width=True):
            st.session_state.sessions = []
            st.session_state.messages = []
            st.session_state.current_session_id = str(uuid.uuid4())
            st.session_state.pending_query = None
            st.rerun()

    st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px solid rgba(32, 31, 29, 0.15);'>", unsafe_allow_html=True)

    # Cấu hình Retrieval & Kho tri thức
    st.markdown("<div class='sidebar-section-title'>Cấu hình Retrieval</div>", unsafe_allow_html=True)
    top_k = st.slider("Số lượng Chunks (top_k)", min_value=3, max_value=10, value=5)

    st.markdown(
        """
        <div style="font-family: 'Inter', sans-serif; font-size: 11px; color: rgba(32, 31, 29, 0.65); line-height: 1.5; margin-top: 8px;">
          <div><b>Phương thức:</b> <span class="badge-tag">Hybrid (BM25 + Dense)</span></div>
          <div style="margin-top: 4px;"><b>Kho tài liệu:</b> 453 Chunks</div>
          <div style="margin-top: 2px;">• QĐ 3626 (Quy chế đào tạo ĐHQGHN)</div>
          <div style="margin-top: 2px;">• QĐ 4618 (Quy định học bổng)</div>
          <div style="margin-top: 2px;">• QĐ 2244 (Cảnh báo học vụ)</div>
          <div style="margin-top: 2px;">• Thông báo tốt nghiệp & BHYT UET</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# Main Chat Header (Replicating Chatbot.html Header)
# ---------------------------------------------------------
st.markdown(
    """
    <div style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 1px solid rgba(32, 31, 29, 0.15); padding-bottom: 12px; margin-bottom: 18px;">
      <div>
        <div style="font-family: 'Cormorant Garamond', Georgia, serif; font-size: 28px; font-weight: 700; color: #201f1d; line-height: 1.1;">Quy chế đào tạo & Dịch vụ sinh viên</div>
        <div style="font-family: 'Lora', Georgia, serif; font-size: 13.5px; color: rgba(32, 31, 29, 0.65); margin-top: 4px;">Hệ thống giải đáp học vụ thông minh — Trường Đại học Công nghệ (VNU-UET)</div>
      </div>
      <div style="text-align: right;">
        <span class="badge-tag" style="background: rgba(34, 139, 34, 0.1); color: #1e701e; border-color: rgba(34, 139, 34, 0.3);">● Sẵn sàng phục vụ</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Empty State Hero View (khi chưa có tin nhắn nào)
# ---------------------------------------------------------
if len(st.session_state.messages) == 0:
    st.markdown(
        """
        <div style="border: 1px solid rgba(32, 31, 29, 0.12); border-radius: 6px; padding: 24px; background: #ffffff; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
          <div style="font-family: 'Cormorant Garamond', serif; font-size: 22px; font-weight: 600; margin-bottom: 6px; color: #201f1d;">Chào mừng bạn đến với Trợ lý Học vụ UET</div>
          <div style="font-size: 14.5px; line-height: 1.6; color: rgba(32, 31, 29, 0.8);">
            Bạn có thể tra cứu nhanh các quy định đào tạo theo tín chỉ, điều kiện tốt nghiệp, mức học bổng, xử lý học vụ và các thông báo chính thức từ Trường ĐH Công nghệ & ĐHQGHN.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# Render Message History
# ---------------------------------------------------------
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"""
            <div class="user-msg-card">
              <div class="user-msg-label">Sinh viên · K66 / 20215412</div>
              <div style="font-size: 14.5px; line-height: 1.6; color: #201f1d;">{msg['content']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        answer_text = msg.get("content", "")
        sources = msg.get("sources", [])
        retrieval_source = msg.get("retrieval_source", "hybrid")

        st.markdown(
            f"""
            <div class="bot-msg-card">
              <div class="bot-msg-label">Trợ lý Quy chế</div>
              <div class="bot-msg-body">{answer_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Hiển thị khối Dẫn chiếu / Citation theo định dạng (1), (2)
        citations = msg.get("citations", [])
        if citations:
            items_html = "".join(
                f"<div style='margin-bottom: 3px;'><b>{c['num']}</b> {c['desc']}</div>"
                for c in citations
            )
            st.markdown(
                f"""
                <div class="citation-box">
                  <div class="citation-label">Dẫn chiếu chính thức</div>
                  <div style="font-size: 13.5px; line-height: 1.6; margin-top: 4px; color: #201f1d;">
                    {items_html}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Khối xem chi tiết Retrieval Context
            num_chunks = len(sources)
            with st.expander(f"📚 Xem nguồn trích dẫn & Retrieval ({retrieval_source.upper()} — {num_chunks} chunks)"):
                for idx, src in enumerate(sources, 1):
                    meta = src.get("metadata", {})
                    t = meta.get("title", "Tài liệu")
                    s_name = meta.get("source", "Tài liệu gốc")
                    d_type = meta.get("doc_type", "legal")
                    sc = src.get("score", 0.0)
                    cid = src.get("id", "N/A")
                    snip = src.get("content", "")
                    
                    st.markdown(f"**[{idx}] {t}** `({d_type.upper()})` — *Rank/Score:* `{sc:.4f}`")
                    st.caption(f"File: `{s_name}` | Chunk ID: `{cid}`")
                    st.markdown(f"> {snip}")
                    st.divider()


# ---------------------------------------------------------
# Suggestion Chips (Gợi ý câu hỏi nhanh)
# ---------------------------------------------------------
st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
chip_col1, chip_col2, chip_col3, chip_col4 = st.columns(4)

with chip_col1:
    if st.button("💰 Học bổng UET bao nhiêu", key="chip_scholarship", use_container_width=True):
        trigger_query("học bổng uet bao nhiêu tiền")

with chip_col2:
    if st.button("🎓 Điều kiện xét tốt nghiệp", key="chip_grad", use_container_width=True):
        trigger_query("Điều kiện để sinh viên được công nhận tốt nghiệp đại học là gì?")

with chip_col3:
    if st.button("📅 Hạn nộp ảnh bằng K66", key="chip_photo", use_container_width=True):
        trigger_query("Sinh viên tốt nghiệp đợt tháng 01/2026 nộp ảnh làm bằng ở đâu và hạn chót khi nào?")

with chip_col4:
    if st.button("⚠️ Cảnh báo học vụ", key="chip_warning", use_container_width=True):
        trigger_query("Điều kiện về điểm trung bình để sinh viên không bị cảnh báo học vụ là gì?")


# ---------------------------------------------------------
# User Query Processing
# ---------------------------------------------------------
user_input = st.chat_input("Nhập câu hỏi về quy chế, học phí, học bổng, thi cử…")

active_query = None
if st.session_state.pending_query:
    active_query = st.session_state.pending_query
    st.session_state.pending_query = None
elif user_input:
    active_query = user_input

if active_query:
    st.session_state.messages.append({"role": "user", "content": active_query})
    save_current_session()
    st.rerun()

# Nếu tin nhắn cuối cùng là của user và chưa có câu trả lời của assistant
if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
    last_query = st.session_state.messages[-1]["content"]

    with st.spinner("Đang đối chiếu quy chế và kiểm chứng dẫn chứng..."):
        gen_result = generate_with_citation(last_query, top_k=top_k)
        answer = gen_result.get("answer", "Tôi không thể xác minh thông tin này từ nguồn hiện có.")
        sources = gen_result.get("sources", [])
        retrieval_source = gen_result.get("retrieval_source", "hybrid")
        citations = gen_result.get("citations", [])

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "retrieval_source": retrieval_source,
            "citations": citations,
        })
        save_current_session()
        st.rerun()


# ---------------------------------------------------------
# Footer Disclaimer (from Chatbot.html)
# ---------------------------------------------------------
st.markdown(
    """
    <div class="disclaimer-text">
      Thông tin mang tính tham khảo trích xuất từ quy chế chính thức ĐHQGHN & UET. Cần xác nhận chính thức, liên hệ Phòng Đào tạo (P.107-G2) hoặc Phòng CTSV (P.210-G2).
    </div>
    """,
    unsafe_allow_html=True,
)

