# src/agents/supervisor.py
from typing import List
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

from configuration import settings
from src.state import ResearchState


SUPERVISOR_SYSTEM_PROMPT = """\
너는 딥리서치 시스템의 Supervisor Agent다.
사용자 질문이 모호하면 최대 3개의 추가 질문을 만들어라.
명확하면 need_clarification=false로 해라.

출력 형식(시스템 파싱용):
need_clarification: true/false
questions:
- ...
- ...
- ...
"""

FINALIZE_SYSTEM_PROMPT = """\
원 질문과 추가 Q/A를 반영해 최종 조사 질문을 한 문단으로 확정해라.
출력은 최종 질문 한 문단만.
"""


def _llm():
    return init_chat_model(
        settings.llm_model,
        temperature=0.2,
        timeout=30,
        max_tokens=300,
    )


def _parse_questions(raw: str) -> List[str]:
    qs: List[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("-"):
            qs.append(line.lstrip("-").strip())
        if len(qs) >= 3:
            break
    return qs


def supervisor_node(state: ResearchState) -> ResearchState:
    question = (state.get("question") or "").strip()

    # 1) 추가 질문 생성(1차)
    raw = _llm().invoke([
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=f"사용자 질문:\n{question}"),
    ]).content.strip()

    need = "need_clarification: true" in raw.lower()
    qs = _parse_questions(raw)

    # LLM이 true라고 해도 질문이 없으면 false 처리
    if not (need and qs):
        return {
            "need_clarification": False,
            "clarifying_questions": qs,
        }

    # 2) 사용자에게 질문하고 답 받기(CLI)
    print("\n추가로 몇 가지만 확인할게요.")
    answers = [input(f"{i}) {q}\n> ").strip() for i, q in enumerate(qs, 1)]

    # 3) 최종 질문 확정(2차)
    qa = "\n".join([f"Q: {q}\nA: {a}" for q, a in zip(qs, answers)])
    final_q = _llm().invoke([
        SystemMessage(content=FINALIZE_SYSTEM_PROMPT),
        HumanMessage(content=f"원 질문:\n{question}\n\n추가 Q/A:\n{qa}"),
    ]).content.strip()

    return {
        "need_clarification": False,
        "clarifying_questions": qs,
        "clarifying_answers": answers,
        "final_question": final_q,
        "question": final_q,  # 다음 노드(planner)가 이 question을 그대로 사용
    }


__all__ = ["supervisor_node"]
