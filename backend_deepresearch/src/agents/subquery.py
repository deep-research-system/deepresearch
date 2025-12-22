from __future__ import annotations
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from configuration import settings
from src.state import ResearchState
from src.prompts.prompts import SUBQUERY_SYSTEM_PROMPT

def _llm():
    return init_chat_model(
        settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=settings.temperature,
        timeout=30,
        max_tokens=400,
    )

def run_deep_research(state: ResearchState) -> ResearchState:
    q = state.final_question or state.question
    text = _llm().invoke([
        SystemMessage(content=SUBQUERY_SYSTEM_PROMPT),
        HumanMessage(content=f"질문: {q}\n최대 {settings.max_subqueries}개의 서브쿼리를 만들어."),
    ]).content.strip()

    raw = [line.strip("-• \t") for line in text.splitlines() if line.strip()]
    dedup = list(dict.fromkeys([s for s in raw if s]))[:settings.max_subqueries]
    state.sub_queries = dedup
    return state
