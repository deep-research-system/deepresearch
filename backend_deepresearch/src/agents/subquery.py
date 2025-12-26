from __future__ import annotations
import json
from typing import List

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from configuration import settings
from src.prompts.prompts import subquery_prompt
from src.state import ResearchState


def _llm():
    return init_chat_model(
        settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=settings.temperature,
        timeout=30,
        max_tokens=400,
    )


def _parse_subqueries(text: str) -> List[str]:
    t = (text or "").strip()
    if not t:
        return []

    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            sq = obj.get("sub_queries")
            if isinstance(sq, list):
                out: List[str] = []
                for x in sq:
                    if isinstance(x, str) and x.strip():
                        out.append(x.strip())
                return out
    except Exception:
        pass

    raw = [line.strip("-• \t") for line in t.splitlines() if line.strip()]
    return [s for s in raw if s]


def subquery(state: ResearchState):
    q = (state.final_question or state.question or "").strip()


    resp = _llm().invoke(
        [
            SystemMessage(content=subquery_prompt),
            HumanMessage(content=f"최종 질문:\n{q}"),
        ]
    )

    sub_queries = _parse_subqueries(getattr(resp, "content", "") or "")
    dedup = list(dict.fromkeys([s for s in sub_queries if s]))[: settings.max_subqueries]

    state.sub_queries = dedup
    yield {"sub_queries": dedup}
