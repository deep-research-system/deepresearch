from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.graph import build_graph
from src.utils.stream import start_graph


class DeepresearchRequest(BaseModel):
    question: str
    addition_questions_answers: Optional[List[str]] =None


app = FastAPI()
graph = build_graph()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 개발 편의. 운영에서는 도메인 고정 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],)


@app.post("/deepresearch")
def deepresearch(Deep: DeepresearchRequest):

    # 프론트로 받은 값들을 BaseState가 이해하도록 키 - 값 넣어줌
    state: Dict[str, Any] = {
        "question" : Deep.question,
        "messages" : [],
        "addition_questions_answers" : Deep.addition_questions_answers
        }
    return start_graph(graph, state)
