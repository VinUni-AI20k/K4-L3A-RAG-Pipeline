# Nh?m K4-L3A ? B?o c?o nh?m RAG Pipeline

## Th?ng tin d? ?n

- Ch? ??: Du l?ch Vi?t Nam ? V?nh H? Long
- Repository: https://github.com/hoanganhb680-arch/K4-L3A-RAG-Pipeline
- Th?nh vi?n:
  - B?i Ho?ng Anh
  - Nguy?n Mai Ho?ng Thi?n
  - Nguy?n Ti?n ??t

## K?t qu? chung

Pipeline ?? ch?y end-to-end:

```text
20 passed in 8.95s
```

C?c th?nh ph?n ch?nh ?? ho?n t?t:

- Thu th?p d? li?u: 3 t?i li?u ph?p l? PDF, 5 b?i vi?t JSON.
- Chu?n h?a: `data/standardized/legal/` v? `data/standardized/news/`.
- Index: ChromaDB persistent, 395 chunks.
- Retrieval:
  - Dense search: Gemini embedding-001.
  - Lexical search: BM25.
  - Fusion: RRF.
  - Fallback: PageIndex n?u thi?u evidence.
- Generation: Gemini c? citation `[Document X]`.
- UI: Streamlit chat hi?n th? c?u tr? l?i v? ngu?n tr?ch xu?t.

## K?t qu? ch?p nh?n

`tests/test_acceptance.py`:

- 3 t?i li?u ph?p l? h?p l?.
- 5 file JSON ?? metadata `url / title / date_crawled / content_markdown`.
- Markdown legal v? news ?? s? l??ng v? c? ?? d?i t?i thi?u.
- Golden dataset 18 cases.
- Report completed.

## K?t qu? h?p ??ng

`tests/test_contracts.py`:

- Document/chunk contract validate.
- Semantic search tr? `dense`, BM25 tr? `bm25`, RRF tr? `hybrid`.
- Fallback d?ng dense cosine score g?c.
- Generation citation map ???c v?o `sources`.

## H?n ch?

- Corpus ch?a ??ng b? ho?n to?n gi?a nh?nh legal hi?n t?i v? ch? ?? V?nh H? Long; c?n ch?t l?i Task 1 ngu?n legal ch?nh th?c.
- PageIndex ch?a c?u h?nh API key n?n fallback hi?n l? safe empty.
- Gemini embedding c? th? g?p gi?i h?n 429 khi s? d?ng free tier.

## H??ng d?n ch?y l?i

```bash
.venv\Scripts\streamlit.exe run app.py --server.port 8501
```

## K? duy?t nh?m

- Ng?y: 2026-09-20
- ??i di?n: B?i Ho?ng Anh
