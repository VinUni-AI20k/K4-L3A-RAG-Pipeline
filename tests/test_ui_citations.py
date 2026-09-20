"""Offline tests cho highlight citation/nguồn (src/ui_citations.py)."""

from src.ui_citations import highlight_evidence, number_citations, order_sources
from tests.test_task5_task10 import _chunk


def test_number_citations_in_order_of_appearance_and_dedup():
    sources = [_chunk("legal/a.md::chunk-1"), _chunk("news/b.md::chunk-7"), _chunk("news/c.md::chunk-2")]
    answer = "Task 2 cần 250 từ [news/b.md::chunk-7]. Task 1 cần 150 từ [legal/a.md::chunk-1], [news/b.md::chunk-7]."
    html_out, cited = number_citations(answer, sources)

    assert cited == ["news/b.md::chunk-7", "legal/a.md::chunk-1"]
    assert html_out.count(">1</span>") == 2 and html_out.count(">2</span>") == 1
    assert "[news/b.md::chunk-7]" not in html_out, "citation thô phải được thay bằng badge"
    assert 'title="news/b.md::chunk-7"' in html_out


def test_number_citations_leaves_unknown_ids_and_escapes_html():
    sources = [_chunk("chunk-0")]
    html_out, cited = number_citations("<b>x</b> [chunk-0] và [unknown]", sources)
    assert cited == ["chunk-0"]
    assert "&lt;b&gt;x&lt;/b&gt;" in html_out
    assert "[unknown]" in html_out


def test_highlight_marks_only_overlapping_sentences():
    content = (
        "You must write at least 250 words for Task 2. "
        "The weather in Colombia is warm and pleasant all year. "
        "Task 1 requires at least 150 words."
    )
    answer = "Bạn phải viết ít nhất 250 words cho Task 2 và 150 words cho Task 1."
    out = highlight_evidence(content, answer)
    assert "<mark" in out
    assert out.count("<mark") == 2
    assert "Colombia" in out and "<mark style=\"background:#fff3a3;color:inherit;padding:0 2px;border-radius:3px;\">The weather" not in out


def test_highlight_without_answer_escapes_only():
    out = highlight_evidence("a < b\nnext line", "")
    assert out == "a &lt; b<br>next line"


def test_highlight_joins_pdf_soft_breaks_and_uses_shared_numbers():
    # Chunk PDF ngắt dòng cứng giữa câu; answer tiếng Việt chỉ trùng số 250.
    content = (
        "For Task 2 of both AC and GT Writing tests, candidates are required to\n"
        "develop a position in relation to a given prompt,\n"
        "using a minimum of 250 words. Ideas should be supported by evidence."
    )
    answer = "Bài Task 2 cần viết tối thiểu 250 từ [legal/ielts-writing-key-assessment-criteria.md::chunk-7]."
    out = highlight_evidence(content, answer)
    assert out.count("<mark") == 1
    assert "<mark" in out and "minimum of 250 words" in out[out.find("<mark"):]
    assert "Ideas should be supported" not in out[out.find("<mark"):out.find("</mark>")]


def test_order_sources_puts_cited_first_with_numbers():
    sources = [_chunk("c0"), _chunk("c1"), _chunk("c2")]
    ordered = order_sources(sources, ["c2", "c0"])
    assert [(n, s["id"]) for n, s in ordered] == [(1, "c2"), (2, "c0"), (None, "c1")]
