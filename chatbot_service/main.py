# chatbot_service/main.py
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from rag_engine import generate_rag_response

load_dotenv()

app = FastAPI(
    title="VitroFit RAG Chatbot API",
    description="RAG-powered fitness assistant backed by OpenRouter",
    version="1.0.0"
)

# Allow React app (port 5173) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="User question or prompt")

class QueryResponse(BaseModel):
    reply: str

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "VitroFit Chatbot (OpenRouter RAG)"}

@app.post("/api/chat", response_model=QueryResponse)
async def chat_endpoint(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        reply = generate_rag_response(request.query)
        return QueryResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))