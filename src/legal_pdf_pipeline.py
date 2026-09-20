"""Page-preserving, citation-ready legal PDF ingestion."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import time
from typing import Literal, Protocol

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REGISTRY_PATH = DATA / "sources.json"
SCHEMA_VERSION = "1.0"
MIN_NATIVE_TEXT_CHARS = 80
STRUCTURING_MODEL = os.getenv("STRUCTURING_MODEL") or os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
BATCH_PAGES = int(os.getenv("LEGAL_STRUCTURING_BATCH_PAGES", "3"))
GEMINI_REQUEST_INTERVAL = float(os.getenv("GEMINI_REQUEST_INTERVAL_SECONDS", "4.2"))


class DocumentMetadata(BaseModel):
    document_title: str | None = None
    document_number: str | None = None
    document_type: str | None = None
    issuer: str | None = None
    issued_date: str | None = None
    effective_date: str | None = None
    signer: str | None = None
    legal_basis: list[str] = Field(default_factory=list)
    source_url: str | None = None


class LegalElement(BaseModel):
    element_type: Literal["chapter", "section", "article", "clause", "point", "paragraph", "other"]
    chapter_number: str | None = None
    chapter_title: str | None = None
    section_number: str | None = None
    section_title: str | None = None
    article_number: str | None = None
    article_title: str | None = None
    clause_number: str | None = None
    point_number: str | None = None
    raw_text: str
    normalized_text: str
    page_start: int
    page_end: int
    confidence: float | None = None


class LegalBatch(BaseModel):
    elements: list[LegalElement]


class OCRAdapter(Protocol):
    name: str
    def ocr_page(self, page) -> dict: ...


class TesseractOCR:
    """Optional Vietnamese OCR adapter; requires Tesseract + vie language data."""
    name = "tesseract"

    def ocr_page(self, page) -> dict:
        import pymupdf as fitz
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("OCR requires optional packages pytesseract and Pillow") from exc
        executable = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if executable.exists():
            pytesseract.pytesseract.tesseract_cmd = str(executable)
        local_tessdata = ROOT / ".tools" / "tessdata"
        config = f'--tessdata-dir {local_tessdata}' if local_tessdata.exists() else ""
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        data = pytesseract.image_to_data(image, lang="vie+eng", config=config, output_type=pytesseract.Output.DICT)
        words, confidences = [], []
        for word, confidence in zip(data["text"], data["conf"]):
            if str(word).strip():
                words.append(str(word))
                try:
                    value = float(confidence)
                    if value >= 0:
                        confidences.append(value / 100)
                except (TypeError, ValueError):
                    pass
        return {"text": " ".join(words), "confidence": sum(confidences) / len(confidences) if confidences else None}


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def native_text_is_usable(text: str) -> bool:
    clean = text.strip()
    if len(clean) < MIN_NATIVE_TEXT_CHARS:
        return False
    useful = sum(char.isalnum() for char in clean) / max(len(clean), 1)
    printable = sum(char.isprintable() for char in clean) / max(len(clean), 1)
    return useful >= 0.35 and printable >= 0.9


def extract_pdf_pages(pdf_path: Path, source_id: str, *, max_pages: int | None = None, skip_ocr: bool = False, ocr: OCRAdapter | None = None) -> tuple[list[dict], dict]:
    import pymupdf as fitz
    ocr = ocr or TesseractOCR()
    pages, errors = [], []
    with fitz.open(pdf_path) as document:
        limit = min(len(document), max_pages) if max_pages else len(document)
        for index in range(limit):
            page_number = index + 1
            try:
                page = document[index]
                native = page.get_text("text").strip()
                if native_text_is_usable(native):
                    record = {"source_id": source_id, "page_number": page_number, "raw_text": native, "extraction_method": "native_pdf", "ocr_engine": None, "ocr_confidence": None}
                elif skip_ocr:
                    record = {"source_id": source_id, "page_number": page_number, "raw_text": native, "extraction_method": "native_pdf", "ocr_engine": None, "ocr_confidence": None}
                else:
                    result = ocr.ocr_page(page)
                    record = {"source_id": source_id, "page_number": page_number, "raw_text": result["text"], "extraction_method": "ocr", "ocr_engine": ocr.name, "ocr_confidence": result.get("confidence")}
                pages.append(record)
                detail = f"confidence={record['ocr_confidence']:.2f}" if record["ocr_confidence"] is not None else f"{len(record['raw_text'])} chars"
                print(f"[{page_number}/{limit}] {record['extraction_method']} — {detail}")
            except Exception as exc:
                error = {"source_id": source_id, "page_number": page_number, "stage": "ocr" if not skip_ocr else "extraction", "error": str(exc)}
                errors.append(error)
                print(f"[ERROR] page {page_number}: {exc}")
        provenance = {"source_id": source_id, "file_name": pdf_path.name, "file_sha256": sha256_file(pdf_path), "total_pages": len(document), "processed_pages": limit, "extracted_at": datetime.now(timezone.utc).isoformat(), "schema_version": SCHEMA_VERSION, "errors": errors}
    return pages, provenance


LEGAL_INSTRUCTION = """Preserve legal wording exactly. Never paraphrase. Never summarize. Never invent missing text. Preserve article numbers, clause numbers, point labels, dates, quantities, names and legal references exactly. normalized_text may only normalize whitespace and obvious OCR artifacts. If uncertain, return null."""


class GeminiStructurer:
    def __init__(self, model: str = STRUCTURING_MODEL, retries: int = 3):
        from google import genai
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is required unless --skip-gemini is used")
        self.client, self.model, self.retries = genai.Client(api_key=key), model, retries

    def structured(self, prompt: str, schema):
        from google.genai import types
        last_error = None
        for attempt in range(self.retries):
            try:
                response = self.client.models.generate_content(model=self.model, contents=prompt, config=types.GenerateContentConfig(system_instruction=LEGAL_INSTRUCTION, response_mime_type="application/json", response_schema=schema, temperature=0))
                time.sleep(GEMINI_REQUEST_INTERVAL)
                return response.parsed
            except Exception as exc:
                last_error = exc
                if attempt + 1 < self.retries:
                    delay = max(GEMINI_REQUEST_INTERVAL, 2 ** attempt)
                    if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                        delay = max(delay, 60 * (attempt + 1))
                    print(f"[RETRY] Gemini attempt {attempt + 2}/{self.retries} in {delay:.1f}s")
                    time.sleep(delay)
        raise RuntimeError(f"Gemini failed after {self.retries} attempts: {last_error}")


def cache_key(source_id: str, content: str, model: str) -> str:
    return hashlib.sha256(f"{source_id}\0{content}\0{model}\0{SCHEMA_VERSION}".encode()).hexdigest()


def fallback_metadata(source: dict) -> DocumentMetadata:
    match = re.search(r"(\d+/\d+/(?:QH\d+|NĐ-CP))", source.get("title", ""))
    kind = "Luật" if source.get("title", "").startswith("Luật") else "Nghị định"
    return DocumentMetadata(document_title=source.get("title"), document_number=match.group(1) if match else None, document_type=kind, issuer=source.get("publisher"), source_url=source.get("landing_url"))


def rule_based_elements(pages: list[dict]) -> list[LegalElement]:
    """Conservative offline parser used for tests/--skip-gemini; never invents text."""
    elements, state = [], {"chapter_number": None, "chapter_title": None, "section_number": None, "section_title": None, "article_number": None, "article_title": None, "clause_number": None}
    heading = re.compile(r"^(Chương\s+([IVXLCDM]+)|Mục\s+(\d+)|Điều\s+(\d+[a-zA-Z]?)\.?)\s*(.*)$", re.I)
    clause = re.compile(r"^(\d+)\.\s+(.+)")
    point = re.compile(r"^([a-zđ])\)\s+(.+)", re.I)
    for page in pages:
        blocks = [b.strip() for b in re.split(r"\n(?=(?:Chương\s+[IVXLCDM]+|Mục\s+\d+|Điều\s+\d+|\d+\.|[a-zđ]\)))", page["raw_text"], flags=re.I) if b.strip()]
        for block in blocks:
            first = block.splitlines()[0].strip()
            match = heading.match(first)
            element_type = "paragraph"
            point_number = None
            if match:
                if match.group(2):
                    state.update(chapter_number=match.group(2), chapter_title=match.group(5) or None, section_number=None, section_title=None, article_number=None, article_title=None, clause_number=None); element_type = "chapter"
                elif match.group(3):
                    state.update(section_number=match.group(3), section_title=match.group(5) or None, article_number=None, article_title=None, clause_number=None); element_type = "section"
                else:
                    state.update(article_number=match.group(4), article_title=match.group(5) or None, clause_number=None); element_type = "article"
            elif clause.match(first):
                state["clause_number"] = clause.match(first).group(1); element_type = "clause"
            elif point.match(first):
                point_number = point.match(first).group(1); element_type = "point"
            elements.append(LegalElement(element_type=element_type, point_number=point_number, raw_text=block, normalized_text=re.sub(r"\s+", " ", block).strip(), page_start=page["page_number"], page_end=page["page_number"], **state))
    return elements


def legal_path(record: dict) -> str:
    parts = []
    for key, label in (("chapter_number", "Chương"), ("section_number", "Mục"), ("article_number", "Điều"), ("clause_number", "Khoản"), ("point_number", "Điểm")):
        if record.get(key): parts.append(f"{label} {record[key]}")
    return " > ".join(parts)


def stable_record_id(record: dict) -> str:
    page = str(record["page_start"]) if record["page_start"] == record["page_end"] else f"{record['page_start']}-{record['page_end']}"
    parts = [record["source_id"], f"p{page}"]
    for key, label in (("article_number", "article"), ("clause_number", "clause"), ("point_number", "point")):
        if record.get(key): parts.append(f"{label}{record[key]}")
    return "::".join(parts)


def normalize_records(elements: list[LegalElement], metadata: DocumentMetadata, provenance: dict, pages: list[dict], model: str) -> list[dict]:
    by_page = {p["page_number"]: p for p in pages}; records, seen = [], set()
    for element in elements:
        record = {**metadata.model_dump(), **element.model_dump(), "source_id": provenance["source_id"], "file_name": provenance["file_name"], "file_sha256": provenance["file_sha256"], "structuring_model": model, "schema_version": SCHEMA_VERSION}
        # Models occasionally include the Vietnamese label despite the schema
        # asking for the number/letter only. Strip labels, never infer values.
        for key, prefix in (("article_number", "Điều"), ("clause_number", "Khoản"), ("point_number", "Điểm")):
            value = record.get(key)
            if value:
                value = re.sub(rf"^\s*{prefix}\s+", "", str(value), flags=re.I).strip()
                record[key] = value.rstrip(".) ")
        record["legal_path"] = legal_path(record)
        methods = [by_page[p]["extraction_method"] for p in range(record["page_start"], record["page_end"] + 1) if p in by_page]
        record["extraction_method"] = "ocr" if "ocr" in methods else "native_pdf"
        ocr_pages = [by_page[p] for p in range(record["page_start"], record["page_end"] + 1) if p in by_page and by_page[p]["extraction_method"] == "ocr"]
        record["ocr_engine"] = ocr_pages[0]["ocr_engine"] if ocr_pages else None
        vals = [p["ocr_confidence"] for p in ocr_pages if p["ocr_confidence"] is not None]
        record["ocr_confidence"] = sum(vals) / len(vals) if vals else None
        base = stable_record_id(record); rid = base
        if rid in seen:
            rid += "::" + hashlib.sha256(record["normalized_text"].encode()).hexdigest()[:8]
        record["id"] = rid; seen.add(rid); records.append(record)
    validate_legal_records(records)
    return records


def validate_legal_records(records: list[dict]) -> None:
    ids = set()
    for record in records:
        if not record.get("source_id") or not re.fullmatch(r"[0-9a-f]{64}", record.get("file_sha256", "")): raise ValueError("Missing source_id or valid file SHA256")
        if record.get("page_start", 0) < 1 or record.get("page_end", 0) < record["page_start"]: raise ValueError("Invalid page range")
        if not record.get("normalized_text", "").strip(): raise ValueError("normalized_text must not be empty")
        for key in ("article_number", "clause_number"):
            if record.get(key) and not re.fullmatch(r"\d+[A-Za-z]?", record[key]): raise ValueError(f"Invalid {key}: {record[key]}")
        if record["legal_path"] != legal_path(record): raise ValueError("Inconsistent legal_path")
        if record["id"] in ids: raise ValueError(f"Duplicate ID: {record['id']}")
        ids.add(record["id"])


def write_outputs(source_id: str, pages: list[dict], provenance: dict, metadata: DocumentMetadata, records: list[dict]) -> None:
    extracted = DATA / "extracted" / "legal" / source_id; structured = DATA / "structured" / "legal"; standardized = DATA / "standardized" / "legal"
    for directory in (extracted, structured, standardized): directory.mkdir(parents=True, exist_ok=True)
    (extracted / "document_metadata.json").write_text(json.dumps({**provenance, **metadata.model_dump()}, ensure_ascii=False, indent=2), encoding="utf-8")
    for page in pages: (extracted / f"page_{page['page_number']:03d}.json").write_text(json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8")
    jsonl = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + ("\n" if records else "")
    (structured / f"{source_id}.jsonl").write_text(jsonl, encoding="utf-8"); (standardized / f"{source_id}.jsonl").write_text(jsonl, encoding="utf-8")
    md = []
    for r in records:
        md.append(f"---\nsource_id: {source_id}\ndocument_number: {r.get('document_number')}\nissuer: {r.get('issuer')}\npage_start: {r['page_start']}\npage_end: {r['page_end']}\nlegal_path: \"{r['legal_path']}\"\nsource_url: {r.get('source_url')}\n---\n\n{r['normalized_text']}\n")
    (standardized / f"{source_id}.md").write_text("\n".join(md), encoding="utf-8")


def process_pdf(source_id: str, *, max_pages: int | None = None, skip_ocr: bool = False, skip_gemini: bool = False, force: bool = False, ocr: OCRAdapter | None = None) -> list[dict]:
    source = load_registry()[source_id]; pdf = DATA / "landing" / "legal" / source["local_filename"]
    if not pdf.exists(): raise FileNotFoundError(pdf)
    print(f"[SOURCE] {source_id}")
    output_path = DATA / "structured" / "legal" / f"{source_id}.jsonl"
    metadata_path = DATA / "extracted" / "legal" / source_id / "document_metadata.json"
    if not force and output_path.exists() and metadata_path.exists():
        cached_meta = json.loads(metadata_path.read_text(encoding="utf-8"))
        wanted_pages = max_pages or cached_meta.get("total_pages")
        if cached_meta.get("file_sha256") == sha256_file(pdf) and cached_meta.get("processed_pages") == wanted_pages and cached_meta.get("structuring_model", STRUCTURING_MODEL if not skip_gemini else "rule-based-offline") == (STRUCTURING_MODEL if not skip_gemini else "rule-based-offline"):
            print(f"[CACHE] {source_id} hit")
            return [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    pages, provenance = extract_pdf_pages(pdf, source_id, max_pages=max_pages, skip_ocr=skip_ocr, ocr=ocr)
    provenance.update(landing_url=source.get("landing_url"), pdf_url=source.get("pdf_url"), structuring_model=STRUCTURING_MODEL if not skip_gemini else "rule-based-offline")
    metadata = fallback_metadata(source)
    elements = rule_based_elements(pages)
    if not skip_gemini:
        gemini = GeminiStructurer()
        sample = "\n\n".join(f"PAGE {p['page_number']}:\n{p['raw_text']}" for p in (pages[:3] + pages[-1:]))
        metadata = gemini.structured(f"Extract document metadata from source registry {json.dumps(source, ensure_ascii=False)} and pages:\n{sample}", DocumentMetadata)
        elements = []
        for start in range(0, len(pages), BATCH_PAGES):
            batch = pages[start:start+BATCH_PAGES]; content = "\n\n".join(f"PAGE {p['page_number']}:\n{p['raw_text']}" for p in batch)
            try: elements.extend(gemini.structured(f"Extract every legal element with exact page provenance:\n{content}", LegalBatch).elements)
            except Exception as exc: provenance["errors"].append({"source_id":source_id,"page_number":batch[0]["page_number"],"stage":"structuring","error":str(exc)})
    records = normalize_records(elements, metadata, provenance, pages, STRUCTURING_MODEL if not skip_gemini else "rule-based-offline")
    write_outputs(source_id, pages, provenance, metadata, records)
    print(f"[VALIDATE] {len(records)} records\n[SAVED] data/structured/legal/{source_id}.jsonl\n[DONE]")
    return records


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--source-id"); parser.add_argument("--max-pages", type=int); parser.add_argument("--skip-ocr", action="store_true"); parser.add_argument("--skip-gemini", action="store_true"); parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv); sources = [args.source_id] if args.source_id else [k for k,v in load_registry().items() if v.get("source_type") == "legal"]
    for source_id in sources: process_pdf(source_id, max_pages=args.max_pages, skip_ocr=args.skip_ocr, skip_gemini=args.skip_gemini, force=args.force)


if __name__ == "__main__": main()
