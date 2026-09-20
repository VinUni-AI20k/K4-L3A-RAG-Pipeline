import hashlib
from src.citations import format_citation, validate_citations
from src.legal_pdf_pipeline import legal_path, stable_record_id, native_text_is_usable

def test_legal_path_and_stable_id():
    record={"source_id":"nd28_2026","page_start":13,"page_end":14,"chapter_number":"II","section_number":None,"article_number":"4","clause_number":"2","point_number":"a"}
    assert legal_path(record)=="Chương II > Điều 4 > Khoản 2 > Điểm a"
    assert stable_record_id(record)=="nd28_2026::p13-14::article4::clause2::pointa"

def test_citation_formatters_and_fake_id():
    assert format_citation({"title":"Nghị định 28/2026/NĐ-CP","article_number":"4","clause_number":"2","point_number":"a","page_start":13,"page_end":14})=="Nghị định 28/2026/NĐ-CP — Điều 4, Khoản 2, Điểm a — Trang 13–14"
    assert not validate_citations("Khẳng định [E9]", [{},{}])["valid"]

def test_native_quality_heuristic():
    assert not native_text_is_usable("scan")
    assert native_text_is_usable("Điều 1. " + "Nội dung quy định pháp luật 123. "*5)
