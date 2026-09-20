"""
Bonus — Highlight citation và nguồn trong UI.

Thuần Python, không phụ thuộc Streamlit để test offline được. app.py dùng:

    number_citations(answer, sources)  -> (answer_html, cited_ids)
        Thay mỗi "[chunk-id]" trong câu trả lời bằng badge số [1], [2]... theo
        thứ tự xuất hiện; cited_ids là các chunk ID được cite, cùng thứ tự.
    highlight_evidence(content, answer) -> html
        Bọc <mark> quanh các câu trong chunk trùng nhiều từ với câu trả lời,
        để người dùng thấy đoạn nào là bằng chứng.

Chỉ escape HTML của nội dung do LLM/tài liệu sinh ra; markup thêm vào là của
ta nên dùng được với st.markdown(unsafe_allow_html=True).
"""

import html
import re


CITATION = re.compile(r"\[([^\[\]\n]+)\]")
# Tách câu theo dấu chấm hoặc đoạn trống; ngắt dòng đơn (PDF wrap) không tách câu.
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n{2,}")
SOFT_BREAK = re.compile(r"(?<!\n)\n(?!\n)")
NUMBER = re.compile(r"^\d{2,}$")
WORD = re.compile(r"\w+", re.UNICODE)

# Từ ngắn (<= 2 ký tự) và số lẻ thường là nhiễu ("is", "a", "2"); giữ số có
# 3+ chữ số như "150", "250" vì đó là bằng chứng thật trong domain này.
MIN_WORD_LEN = 3
# Từ chức năng phổ biến EN/VI: bỏ đi để tỉ lệ trùng phản ánh từ khoá thật.
# Answer thường là tiếng Việt còn chunk tiếng Anh, nên phần trùng chủ yếu là
# thuật ngữ ("task", "band", "lexical") và số — đó chính là bằng chứng.
STOPWORDS = {
    "the", "and", "for", "you", "your", "must", "are", "this", "that", "with", "from",
    "will", "can", "not", "but", "all", "any", "has", "have", "been", "was", "were",
    "than", "then", "there", "their", "they", "them", "what", "when", "which", "who",
    "how", "into", "also", "more", "most", "some", "such", "may", "its", "should",
    "của", "và", "các", "cho", "trong", "với", "được", "những", "một", "này", "khi",
    "thì", "cần", "phải", "bạn", "là", "có", "không", "để", "theo", "từ", "về", "như",
    "đã", "sẽ", "bài", "câu", "nhất", "ít", "viết",
}
# Answer thường tiếng Việt, chunk tiếng Anh nên phần trùng chỉ là thuật ngữ và
# số; ngưỡng đặt thấp vì highlight thừa ít hại hơn highlight thiếu.
EVIDENCE_THRESHOLD = 0.25  # tỉ lệ từ khoá của câu chunk xuất hiện trong answer...
MIN_SHARED_WORDS = 2       # ...và phải trùng ít nhất từng này từ khoá
MANY_SHARED_WORDS = 4      # hoặc trùng đủ nhiều từ khoá, bất kể câu dài
MIN_SENTENCE_WORDS = 3

BADGE_STYLE = (
    "display:inline-block;padding:0 6px;margin:0 1px;border-radius:8px;"
    "background:#1f77b4;color:#fff;font-size:0.8em;font-weight:600;"
    "vertical-align:super;line-height:1.4;"
)
MARK_STYLE = "background:#fff3a3;color:inherit;padding:0 2px;border-radius:3px;"


def _keywords(text: str) -> set[str]:
    """Từ khoá: bỏ stopword, từ ngắn; giữ số có 2+ chữ số ("20", "150", "250")."""
    return {
        w.lower() for w in WORD.findall(text)
        if (len(w) >= MIN_WORD_LEN or NUMBER.match(w)) and w.lower() not in STOPWORDS
    }


def number_citations(answer: str, sources: list[dict]) -> tuple[str, list[str]]:
    """Trả về (HTML câu trả lời với badge số, danh sách chunk ID theo số)."""
    source_ids = {item["id"] for item in sources}
    cited: list[str] = []

    def _badge(match: re.Match) -> str:
        item_id = match.group(1).strip()
        if item_id not in source_ids:
            return html.escape(match.group(0))
        if item_id not in cited:
            cited.append(item_id)
        number = cited.index(item_id) + 1
        return (
            f'<sup><span style="{BADGE_STYLE}" title="{html.escape(item_id)}">'
            f"{number}</span></sup>"
        )

    # Escape từng đoạn text giữa các citation, giữ badge là HTML của ta.
    parts: list[str] = []
    last = 0
    for match in CITATION.finditer(answer):
        parts.append(html.escape(answer[last:match.start()]))
        parts.append(_badge(match))
        last = match.end()
    parts.append(html.escape(answer[last:]))
    rendered = "".join(parts).replace("\n", "<br>")
    return rendered, cited


def highlight_evidence(content: str, answer: str) -> str:
    """HTML của chunk, các câu là bằng chứng cho answer được bọc <mark>."""
    # Bỏ citation để "legal", "chunk", tên file không bị tính là từ khoá.
    answer_words = _keywords(CITATION.sub(" ", answer))
    if not answer_words:
        return html.escape(content).replace("\n", "<br>")

    pieces: list[str] = []
    for sentence in SENTENCE.split(SOFT_BREAK.sub(" ", content)):
        sentence = sentence.strip()
        if not sentence:
            continue
        words = _keywords(sentence)
        escaped = html.escape(sentence)
        if len(words) >= MIN_SENTENCE_WORDS:
            shared = words & answer_words
            shared_numbers = {w for w in shared if NUMBER.match(w)}
            # Số trùng (250 words, 150 words, 20 words) là bằng chứng mạnh, kể cả
            # khi answer tiếng Việt còn chunk tiếng Anh nên từ thường không trùng.
            if (
                (len(shared) >= MIN_SHARED_WORDS and len(shared) / len(words) >= EVIDENCE_THRESHOLD)
                or len(shared) >= MANY_SHARED_WORDS
                or shared_numbers
            ):
                escaped = f'<mark style="{MARK_STYLE}">{escaped}</mark>'
        pieces.append(escaped)
    return "<br>".join(pieces)


def order_sources(sources: list[dict], cited_ids: list[str]) -> list[tuple[int | None, dict]]:
    """Nguồn được cite trước (kèm số), nguồn không cite sau (số None)."""
    by_id = {item["id"]: item for item in sources}
    ordered: list[tuple[int | None, dict]] = [
        (number, by_id[item_id]) for number, item_id in enumerate(cited_ids, 1) if item_id in by_id
    ]
    ordered += [(None, item) for item in sources if item["id"] not in cited_ids]
    return ordered
