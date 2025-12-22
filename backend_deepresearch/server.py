from __future__ import annotations
from typing import Any, Dict, List, Literal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from src.graph import build_graph
from src.state import ResearchState

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = build_graph()

class InvokeRequest(BaseModel):
    question: str = Field(...)
    active_mode: Literal["chat", "research"] = "research"
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    clarifying_questions: List[str] = Field(default_factory=list)
    clarifying_answers: List[str] = Field(default_factory=list)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/invoke")
def invoke(payload: InvokeRequest):
    state_in = {
        "question": payload.question,
        "messages": payload.messages,
        "clarifying_questions": payload.clarifying_questions,
        "clarifying_answers": payload.clarifying_answers,
    }

    out = graph.invoke(state_in) or {}

    if out.get("need_clarification"):
        return {
            "success": True,
            "data": {
                "need_clarification": True,
                "clarifying_questions": out.get("clarifying_questions", []),
            },
        }

    fq = out.get("final_question") or payload.question
    return {
        "success": True,
        "data": {
            "need_clarification": False,
            "final_question": fq,
            "final_answer": f"명확화된 질문:\n{fq}",
        },
    }