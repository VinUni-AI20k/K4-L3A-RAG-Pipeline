"""
Backend API Server phục vụ Vercel AI Chatbot giao diện Luật Giao Thông RAG.
Chạy trực tiếp bằng lệnh: python api_server.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

from src.task10_generation import generate_with_citation


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title="Vietnam Traffic Law RAG API",
    description="REST API for Hybrid RAG Traffic Law QA Pipeline",
    version="1.0.0",
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Câu hỏi của người dùng")
    top_k: int = Field(default=5, ge=1, le=10, description="Số lượng chunk trích xuất")


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    retrieval_source: str


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "llm_provider": os.getenv("LLM_PROVIDER", "gemini"),
        "llm_model": os.getenv("LLM_MODEL", "gemini-2.5-flash"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"),
    }


@app.get("/api/suggestions")
def get_suggestions():
    return [
        {
            "tag": "🚗 Đào tạo lái xe",
            "query": "Điều kiện để hoàn thành khóa đào tạo lái xe theo quy định mới là gì?",
        },
        {
            "tag": "🪪 Giấy phép lái xe",
            "query": "Thời hạn cấp giấy phép lái xe sau khi đạt sát hạch là bao nhiêu ngày?",
        },
        {
            "tag": "🚸 Thiết bị an toàn trẻ em",
            "query": "Quy định xử phạt khi chở trẻ em dưới 10 tuổi trên ô tô không có thiết bị an toàn?",
        },
        {
            "tag": "📹 Camera xe vận tải",
            "query": "Xe ô tô kinh doanh vận tải hành khách phải lắp camera trong khoang hành khách thế nào?",
        },
    ]


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    try:
        result = generate_with_citation(query=request.query, top_k=request.top_k)
        return ChatResponse(
            answer=result.get("answer", "Không thể tạo phản hồi."),
            sources=result.get("sources", []),
            retrieval_source=result.get("retrieval_source", "none"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Phục vụ file tĩnh cho giao diện Vercel
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Vercel AI Chatbot Server đang khởi động tại: http://localhost:{port}")
    uvicorn.run("api_server:app", host="0.0.0.0", port=port, reload=True)
