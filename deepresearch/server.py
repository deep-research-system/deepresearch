"""FastAPI application exposing the DeepResearch graph as a web API.

This module defines a small REST API used by the Next.js frontend to invoke
the research graph. It loads environment variables via ``configuration`` and
supports CORS so that the frontend can communicate with it during local
development. The ``/invoke`` endpoint accepts a question, the desired mode
(``"chat"`` or ``"research"``), and an optional message history. It returns
the raw graph state as JSON on success.

To run this server locally invoke ``python server.py`` from the
``deepresearch`` directory. This starts a Uvicorn server on port 2024.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn

from src.graph import build_graph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

# Instantiate the FastAPI app. The title is used for Swagger docs if enabled.
app = FastAPI(title="DeepResearch API")

# Allow cross‑origin requests from any origin during development. You can
# restrict this list in production by specifying explicit origins (e.g.
# ["http://localhost:3000"]).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = build_graph()


class GraphMessage(BaseModel):
    """Represents a message exchanged with the agent.

    Each message has a role ("user" or "assistant") and textual content.
    """

    role: str
    content: str

class GraphInput(BaseModel):
    question: str
    active_mode: str = "research"
    messages: List[GraphMessage] = []
    clarifying_questions: List[str] = []
    clarifying_answers: List[str] = []


def _to_lc_message(role: str, content: str) -> BaseMessage:
    r = (role or "").lower()
    if r in ("user", "human"):
        return HumanMessage(content=content)
    if r in ("assistant", "ai"):
        return AIMessage(content=content)
    if r == "system":
        return SystemMessage(content=content)
    # 기본값
    return HumanMessage(content=content)

def _to_json_message(m: Any) -> Dict[str, str]:
    # 이미 dict면 그대로
    if isinstance(m, dict):
        return {"role": m.get("role", ""), "content": m.get("content", "")}

    # LangChain 메시지 객체면 type 기반으로 role 변환
    if isinstance(m, BaseMessage):
        t = getattr(m, "type", "")  # "human" | "ai" | "system"
        role_map = {"human": "user", "ai": "assistant", "system": "system"}
        return {"role": role_map.get(t, t or "user"), "content": getattr(m, "content", "")}

    return {"role": "unknown", "content": str(m)}



@app.post("/invoke")
async def invoke_graph(input_data: GraphInput):
    # 1) 프론트(JSON) → LangChain BaseMessage 리스트로 변환
    lc_messages = [_to_lc_message(m.role, m.content) for m in input_data.messages]

    result = graph.invoke(
        {
            "question": input_data.question,
            "active_mode": input_data.active_mode,
            "messages": lc_messages,  # 중요: 그래프 내부는 BaseMessage로 통일
            "clarifying_questions": input_data.clarifying_questions,
            "clarifying_answers": input_data.clarifying_answers,
        }
    )

    # 2) 결과 messages를 JSON으로 직렬화해서 반환
    out = dict(result)
    if "messages" in out:
        out["messages"] = [_to_json_message(m) for m in out["messages"]]

    return {"success": True, "data": out}


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Simple health check endpoint used by the frontend to verify connectivity."""
    return {"status": "healthy", "graph": "deep_research"}


if __name__ == "__main__":
    # When executed directly this will start the Uvicorn web server. ``reload``
    # is disabled by default to avoid spawning multiple processes in this
    # container. Adjust host/port as necessary for your environment.
    uvicorn.run(app, host="0.0.0.0", port=8000)
