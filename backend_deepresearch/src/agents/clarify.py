from __future__ import annotations
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from configuration import settings
from src.state import ResearchState
from src.prompts.prompts import SUPERVISOR_SYSTEM_PROMPT, FINALIZE_SYSTEM_PROMPT

def _llm():
    return init_chat_model(settings.llm_model, api_key=settings.openai_api_key)

def clarify(state: ResearchState) -> ResearchState:
    if state.final_question:
        return state

    if state.clarifying_questions and state.clarifying_answers:
        qa = "\n".join([f"Q: {q}\nA: {a}" for q, a in zip(state.clarifying_questions, state.clarifying_answers)])
        text = _llm().invoke([
            SystemMessage(content=FINALIZE_SYSTEM_PROMPT),
            HumanMessage(content=f"원 질문:\n{state.question}\n\n추가 Q/A:\n{qa}"),
        ]).content.strip()
        state.need_clarification = False
        state.final_question = text or state.question
        return state

    text = _llm().invoke([
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=f"사용자 질문:\n{state.question}"),
    ]).content.strip()

    low = text.lower()
    state.need_clarification = "need_clarification: true" in low

    qs = []
    if "questions:" in text:
        after = text.split("questions:", 1)[1]
        for line in after.splitlines():
            line = line.strip()
            if line.startswith("- "):
                qs.append(line[2:].strip())
    state.clarifying_questions = qs[:3]

    if not state.need_clarification:
        state.final_question = state.question

    return state
