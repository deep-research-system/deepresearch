from __future__ import annotations
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from configuration import settings
from src.state import ResearchState
from src.prompts.prompts import subquery_prompt


def _llm():
    return init_chat_model(
        settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=settings.temperature,
        timeout=30,
        max_tokens=400,
    )


def subquery(state: ResearchState):
    q = state.final_question or state.question

    buf: list[str] = []
    for chunk in _llm().stream(
        [
            SystemMessage(content=subquery_prompt),
            HumanMessage(content=f"질문: {q}\n최대 {settings.max_subqueries}개의 서브쿼리를 만들어."),
        ]
    ):
        if chunk.content:
            buf.append(chunk.content)
            yield {"type": "assistant_text", "content": chunk.content}

    text = "".join(buf).strip()
    raw = [line.strip("-• \t") for line in text.splitlines() if line.strip()]
    dedup = list(dict.fromkeys([s for s in raw if s]))[: settings.max_subqueries]

    state.sub_queries = dedup

    yield {"sub_queries": dedup}
