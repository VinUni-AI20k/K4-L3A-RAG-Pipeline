"""Gemini generation with evidence IDs and citation validation."""
import os
from dotenv import load_dotenv
from .task9_retrieval_pipeline import retrieve
load_dotenv(); TOP_K=5;TOP_P=.9;TEMPERATURE=.3
LLM_PROVIDER=os.getenv("LLM_PROVIDER","gemini");LLM_MODEL=os.getenv("LLM_MODEL","gemini-3.5-flash-lite")
SYSTEM_PROMPT="""Answer only from provided evidence. Every material factual claim must be supported by one or more evidence IDs such as [E1]. Never invent evidence IDs. Never invent URLs. Never invent article numbers, clause numbers, dates or legal references. If evidence is insufficient, say that the available corpus is insufficient to verify the claim."""

def reorder_for_llm(chunks:list[dict])->list[dict]:
    if len(chunks)<=2:return list(chunks)
    return chunks[::2]+chunks[1::2][::-1]

def format_context(chunks:list[dict])->str:
    parts=[]
    for i,x in enumerate(chunks,1):
        m=x["metadata"];lines=[f"[E{i}]",f"Source type: {m.get('doc_type')}",f"Title: {m.get('title')}"]
        if m.get("doc_type")=="legal":
            start,end=m.get("page_start"),m.get("page_end");pages=str(start) if start==end else f"{start}–{end}"
            lines += [f"Issuer: {m.get('source')}",f"Legal path: {m.get('legal_path') or 'N/A'}",f"Pages: {pages}"]
        else: lines += [f"Publisher: {m.get('publisher') or m.get('source')}",f"Published: {m.get('published_date')}"]
        lines += [f"Source URL: {m.get('url') or 'N/A'}","Content:",x["content"]];parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)

def call_llm(system_prompt:str,user_message:str)->str:
    if LLM_PROVIDER.lower()!="gemini":raise ValueError("Only Gemini generation is supported")
    from google import genai
    from google.genai import types
    key=os.getenv("GEMINI_API_KEY")
    if not key:raise RuntimeError("GEMINI_API_KEY is required")
    return genai.Client(api_key=key).models.generate_content(model=LLM_MODEL,contents=user_message,config=types.GenerateContentConfig(system_instruction=system_prompt,temperature=TEMPERATURE,top_p=TOP_P)).text

def generate_with_citation(query:str,top_k:int=TOP_K)->dict:
    from .citations import validate_citations
    chunks=retrieve(query,top_k=top_k)
    if not chunks:return {"answer":"Tôi không thể xác minh thông tin này từ nguồn hiện có.","sources":[],"retrieval_source":"none"}
    ordered=reorder_for_llm(chunks)
    try:answer=call_llm(SYSTEM_PROMPT,f"Evidence:\n{format_context(ordered)}\n\nQuestion: {query}")
    except Exception:return {"answer":"Tôi không thể xác minh thông tin này từ nguồn hiện có.","sources":[],"retrieval_source":"none"}
    if not validate_citations(answer,ordered)["valid"]:answer="Tôi không thể xác minh câu trả lời vì citation do mô hình tạo không hợp lệ."
    return {"answer":answer,"sources":chunks,"retrieval_source":chunks[0]["retrieval_method"]}
if __name__=="__main__":print(generate_with_citation("test query"))
