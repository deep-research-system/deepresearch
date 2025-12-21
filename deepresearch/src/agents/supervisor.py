# src/agents/supervisor.py
from typing import List, Literal
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from pydantic import Field

from configuration import settings
from src.state import ResearchState

from langchain_core.messages import get_buffer_string


Mode = Literal["simple_chat", "deep_research"]

SIMPLE_CHAT_PROMPT = """\
너는 친절한 AI 어시스턴트야. 간단하고 자연스럽게 답변해.

대화 기록:
{messages}

이전 리서치 결과:
{research_summary}

사용자 질문: {question}

간단히 답변해. 딥리서치가 필요하면 "자세한 조사는 '딥리서치 모드'에서 가능해요"라고 말해.
"""

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

def _chat_llm():
    """ 간단한 대화용 LLM """
    return init_chat_model(
        settings.llm_model,
        temperature=0.7,
        timeout=10,
        max_tokens=200,
    )

def _llm():
    return init_chat_model(
        settings.llm_model,
        temperature=0.2,
        timeout=30,
        max_tokens=300,
    )

#  앞의 3개의 질문만 추출
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
    """
    Decide whether to enter simple chat mode or the full deep research pipeline.

    The state may specify an ``active_mode`` key with value ``"chat"`` to
    trigger the simple chat handler. Otherwise the deep research handler runs.
    Default mode is ``"research"``.
    """
    # Pull the requested mode from the state. If none is provided default to
    # research. Note: previously this variable was misspelled as ``acitve_mode``.
    active_mode = state.get("active_mode", "research")

    # In chat mode we skip the full research pipeline and immediately produce a
    # response based on the short dialogue history. All relevant state updates
    # (messages, completion flag) are handled by ``simple_chat_handler``.
    if active_mode == "chat":
        return simple_chat_handler(state)

    # Otherwise run the deep research handler. This will drive the graph
    # through the planner, retriever, verifier, writer and reviewer nodes.
    return deep_research_handler(state)


def simple_chat_handler(state: ResearchState) -> ResearchState:
    question = state.get("question", "")
    messages = state.get("messages", [])

    # BaseMessage 리스트를 사람이 읽는 대화 로그 문자열로 변환
    history_text = get_buffer_string(messages[-8:]) if messages else ""

    prompt = SIMPLE_CHAT_PROMPT.format(
        messages=history_text,
        research_summary="없음",
        question=question,
    )

    response = _chat_llm().invoke([HumanMessage(content=prompt)])

    # 그래프 내부는 메시지 객체로 유지하는 게 정석(add_messages와 궁합)
    return {
        "is_complete": True,
        "final_answer": response.content,
        "messages": [AIMessage(content=response.content)],
    }


def deep_research_handler(state: ResearchState) -> ResearchState:
    question = (state.get("question") or "").strip()

    # (A) 이미 프론트에서 추가 답을 보내온 경우: 최종 질문 확정 후 계속 진행
    qs = state.get("clarifying_questions") or []
    answers = state.get("clarifying_answers") or []
    if qs and answers and len(qs) == len(answers):
        qa = "\n".join([f"Q: {q}\nA: {a}" for q, a in zip(qs, answers)])
        final_q = _llm().invoke([
            SystemMessage(content=FINALIZE_SYSTEM_PROMPT),
            HumanMessage(content=f"원 질문:\n{question}\n\n추가 Q/A:\n{qa}"),
        ]).content.strip()

        return {
            "need_clarification": False,
            "final_question": final_q,
            "question": final_q,   # planner가 이걸 사용
        }

    # (B) 1차: 추가 질문 생성
    raw = _llm().invoke([
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=f"사용자 질문:\n{question}"),
    ]).content.strip()

    need = "need_clarification: true" in raw.lower()
    qs = _parse_questions(raw)

    if need and qs:
        # 웹에서는 input()으로 받지 말고 프론트로 질문을 돌려보낸 뒤 종료
        return {
            "need_clarification": True,
            "clarifying_questions": qs,
            "is_complete": True,   # supervisor에서 종료시키기 위한 플래그
        }

    return {
        "need_clarification": False,
        "clarifying_questions": qs,
    }


__all__ = ["supervisor_node"]
