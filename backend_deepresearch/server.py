from __future__ import annotations
from typing import Any, Dict, List, Literal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from src.graph import build_graph
from src.utils.stream import stream_graph

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 그래프 빌드
graph = build_graph()

# 요청 모델 정의
class InvokeRequest(BaseModel):
    question: str = Field(...)
    active_mode: Literal["chat", "research"] = "research"
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    clarifying_questions: List[str] = Field(default_factory=list)
    clarifying_answers: List[str] = Field(default_factory=list)

# uvicorn확인용
@app.get("/health")
def health():
    return {"status": "ok"}


# 스트리밍 엔드포인트
@app.post("/invoke/stream")
def invoke_stream(payload: InvokeRequest):
    state_in = {
        "question": payload.question,
        "messages": payload.messages,
        "clarifying_questions": payload.clarifying_questions,
        "clarifying_answers": payload.clarifying_answers,
    }
    return stream_graph(graph, state_in)
