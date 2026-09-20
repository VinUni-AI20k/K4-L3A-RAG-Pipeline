// ==========================================================================
// VERCEL AI CHATBOT — FRONTEND CONTROLLER
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const chatContainer = document.getElementById("chatContainer");
  const messagesFeed = document.getElementById("messagesFeed");
  const heroScreen = document.getElementById("heroScreen");
  const suggestionGrid = document.getElementById("suggestionGrid");
  const topKSelect = document.getElementById("topKSelect");
  const newChatBtn = document.getElementById("newChatBtn");
  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebar = document.getElementById("sidebar");
  const historyList = document.getElementById("historyList");

  // Modal elements
  const citationsModal = document.getElementById("citationsModal");
  const closeModalBtn = document.getElementById("closeModalBtn");
  const modalBody = document.getElementById("modalBody");

  let isGenerating = false;
  let chatHistory = JSON.parse(localStorage.getItem("rag_chat_history") || "[]");
  let currentSourcesMap = new Map(); // id -> source object

  // Configure marked options
  if (window.marked) {
    marked.setOptions({
      breaks: true,
      gfm: true,
      highlight: function(code, lang) {
        if (window.hljs && lang && hljs.getLanguage(lang)) {
          try {
            return hljs.highlight(code, { language: lang }).value;
          } catch (e) {}
        }
        return code;
      }
    });
  }

  // 1. Load Suggestions
  const defaultSuggestions = [
    {
      tag: "🚗 Đào tạo lái xe",
      query: "Điều kiện để hoàn thành khóa đào tạo lái xe theo quy định mới là gì?"
    },
    {
      tag: "🪪 Giấy phép lái xe",
      query: "Thời hạn cấp giấy phép lái xe sau khi đạt sát hạch là bao nhiêu ngày?"
    },
    {
      tag: "🚸 Thiết bị an toàn trẻ em",
      query: "Quy định xử phạt khi chở trẻ em dưới 10 tuổi trên ô tô không có thiết bị an toàn?"
    },
    {
      tag: "📹 Camera xe vận tải",
      query: "Xe ô tô kinh doanh vận tải hành khách phải lắp camera trong khoang hành khách thế nào?"
    }
  ];

  function renderSuggestions() {
    suggestionGrid.innerHTML = "";
    defaultSuggestions.forEach((item) => {
      const card = document.createElement("div");
      card.className = "suggestion-card";
      card.innerHTML = `
        <span class="card-tag">${item.tag}</span>
        <span class="card-query">${item.query}</span>
      `;
      card.addEventListener("click", () => {
        chatInput.value = item.query;
        updateInputHeight();
        validateInput();
        handleSendMessage();
      });
      suggestionGrid.appendChild(card);
    });
  }

  renderSuggestions();
  renderHistory();

  // 2. Input management & auto-resize
  function updateInputHeight() {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + "px";
  }

  function validateInput() {
    const hasText = chatInput.value.trim().length > 0;
    sendBtn.disabled = !hasText || isGenerating;
  }

  chatInput.addEventListener("input", () => {
    updateInputHeight();
    validateInput();
  });

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled) {
        handleSendMessage();
      }
    }
  });

  sendBtn.addEventListener("click", handleSendMessage);

  // 3. Send message handler
  async function handleSendMessage() {
    const query = chatInput.value.trim();
    if (!query || isGenerating) return;

    // Reset input
    chatInput.value = "";
    updateInputHeight();
    validateInput();

    // Hide hero screen
    heroScreen.style.display = "none";

    // Append User Message
    appendUserMessage(query);

    // Save to history sidebar
    addChatToHistory(query);

    // Prepare Assistant placeholder
    const { assistantRow, contentEl, citationsEl } = createAssistantRow();
    contentEl.innerHTML = `
      <div style="display:flex; align-items:center; gap:8px; color:var(--text-muted); font-size:13px;">
        <span class="status-dot" style="animation: pulse 1s infinite;"></span>
        <span>Đang truy xuất văn bản pháp luật và tổng hợp câu trả lời...</span>
      </div>
    `;
    scrollToBottom();

    isGenerating = true;
    validateInput();

    const topK = parseInt(topKSelect.value || "5", 10);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: topK })
      });

      if (!response.ok) {
        throw new Error(`Server status: ${response.status}`);
      }

      const data = await response.json();
      const rawAnswer = data.answer || "Không nhận được phản hồi từ hệ thống.";
      const sources = data.sources || [];

      // Map sources for citation click
      currentSourcesMap.clear();
      sources.forEach((s, idx) => {
        currentSourcesMap.set(`doc_${idx + 1}`, s);
      });

      // Typewriter / Markdown Render
      await renderAnswerWithCitations(contentEl, rawAnswer);

      // Render Citations Bar (Perplexity style)
      renderCitationsBar(citationsEl, sources, data.retrieval_source);

    } catch (err) {
      console.error(err);
      contentEl.innerHTML = `
        <div style="color:#ef4444; font-size:13px; padding:8px 12px; background:rgba(239,68,68,0.1); border-radius:8px; border:1px solid rgba(239,68,68,0.2);">
          ⚠️ Lỗi kết nối: ${err.message}. Vui lòng kiểm tra lại server backend.
        </div>
      `;
    } finally {
      isGenerating = false;
      validateInput();
      scrollToBottom();
    }
  }

  // 4. UI Builders
  function appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "message-row user";
    row.innerHTML = `<div class="user-bubble">${escapeHtml(text)}</div>`;
    messagesFeed.appendChild(row);
    scrollToBottom();
  }

  function createAssistantRow() {
    const row = document.createElement("div");
    row.className = "message-row assistant";
    row.innerHTML = `
      <div class="assistant-avatar">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2L2 22h20L12 2z"/>
        </svg>
      </div>
      <div class="assistant-body">
        <div class="assistant-text"></div>
        <div class="citations-bar" style="display:none;"></div>
        <div class="action-row">
          <button class="action-btn copy-btn" title="Sao chép nội dung">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            <span>Copy</span>
          </button>
        </div>
      </div>
    `;
    messagesFeed.appendChild(row);

    const contentEl = row.querySelector(".assistant-text");
    const citationsEl = row.querySelector(".citations-bar");
    const copyBtn = row.querySelector(".copy-btn");

    copyBtn.addEventListener("click", () => {
      const text = contentEl.innerText;
      navigator.clipboard.writeText(text).then(() => {
        copyBtn.innerHTML = `
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <span style="color:#34d399;">Copied</span>
        `;
        setTimeout(() => {
          copyBtn.innerHTML = `
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            <span>Copy</span>
          `;
        }, 2000);
      });
    });

    return { assistantRow: row, contentEl, citationsEl };
  }

  async function renderAnswerWithCitations(targetEl, rawMarkdown) {
    if (window.marked) {
      targetEl.innerHTML = marked.parse(rawMarkdown);
    } else {
      targetEl.innerText = rawMarkdown;
    }
  }

  function renderCitationsBar(citationsEl, sources, retrievalSource) {
    if (!sources || sources.length === 0) {
      citationsEl.style.display = "none";
      return;
    }

    citationsEl.style.display = "flex";
    citationsEl.innerHTML = `<span class="citations-label">Nguồn căn cứ (${sources.length}):</span>`;

    sources.forEach((doc, idx) => {
      const pill = document.createElement("button");
      pill.className = "citation-pill";
      const title = doc.metadata?.title || `Văn bản ${idx + 1}`;
      pill.innerHTML = `
        <span class="doc-num">[${idx + 1}]</span>
        <span class="doc-title" title="${escapeHtml(title)}">${escapeHtml(title)}</span>
      `;
      pill.addEventListener("click", () => {
        openCitationModal(sources, idx);
      });
      citationsEl.appendChild(pill);
    });
  }

  // 5. Modal Display
  function openCitationModal(sources, activeIndex = 0) {
    modalBody.innerHTML = "";
    sources.forEach((doc, idx) => {
      const metadata = doc.metadata || {};
      const score = doc.score ? Number(doc.score).toFixed(4) : "N/A";
      const method = doc.retrieval_method ? doc.retrieval_method.toUpperCase() : "HYBRID";
      const sourcePath = metadata.source || "Nguồn nội bộ";
      const title = metadata.title || `Văn bản [${idx + 1}]`;

      const item = document.createElement("div");
      item.className = "modal-source-item";
      item.innerHTML = `
        <div class="source-item-top">
          <span class="source-item-title">[${idx + 1}] ${escapeHtml(title)}</span>
          <div class="source-meta-badges">
            <span class="source-badge badge-source">${escapeHtml(sourcePath)}</span>
            <span class="source-badge badge-score">${method} • ${score}</span>
          </div>
        </div>
        <div class="source-quote">"${escapeHtml(doc.content || "")}"</div>
      `;
      modalBody.appendChild(item);
    });

    citationsModal.classList.add("open");
  }

  closeModalBtn.addEventListener("click", () => {
    citationsModal.classList.remove("open");
  });

  citationsModal.addEventListener("click", (e) => {
    if (e.target === citationsModal) {
      citationsModal.classList.remove("open");
    }
  });

  // 6. Chat History Management
  function addChatToHistory(query) {
    const existingIndex = chatHistory.findIndex(h => h.query === query);
    if (existingIndex >= 0) {
      chatHistory.splice(existingIndex, 1);
    }
    chatHistory.unshift({ query, time: Date.now() });
    if (chatHistory.length > 20) chatHistory.pop();
    localStorage.setItem("rag_chat_history", JSON.stringify(chatHistory));
    renderHistory();
  }

  function renderHistory() {
    historyList.innerHTML = "";
    if (chatHistory.length === 0) {
      historyList.innerHTML = `<div style="font-size:12px; color:var(--text-muted); padding:8px 10px;">Chưa có lịch sử</div>`;
      return;
    }
    chatHistory.forEach((item) => {
      const el = document.createElement("div");
      el.className = "history-item";
      el.title = item.query;
      el.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
        <span>${escapeHtml(item.query)}</span>
      `;
      el.addEventListener("click", () => {
        chatInput.value = item.query;
        updateInputHeight();
        validateInput();
        handleSendMessage();
      });
      historyList.appendChild(el);
    });
  }

  newChatBtn.addEventListener("click", () => {
    messagesFeed.innerHTML = "";
    heroScreen.style.display = "block";
    chatInput.value = "";
    updateInputHeight();
    validateInput();
  });

  sidebarToggle.addEventListener("click", () => {
    sidebar.classList.toggle("open");
  });

  function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
