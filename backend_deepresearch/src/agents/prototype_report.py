import json
from typing import Optional, List, Dict, Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage

from configuration import settings, default_report_structure
from src.prompts.prompts import prototype_report_prompt
from src.state import PlannerState  # 경로는 프로젝트 기준에 맞춰 통일


def plan_sections(state: PlannerState):
    topic = state["topic"]
    queries = state.get("queries")
    report_organization = default_report_structure
    feedback = state.get("feedback") or ""
    sections = state.get("sections") or []
    sections = json.dumps(sections, ensure_ascii=False, indent=2)

    # context: 지금 단계에선 "서브쿼리"를 컨텍스트로 넣는 게 가장 간단하고 효과적
    # (나중에 실제 검색 결과로 대체 가능)
    context = "\n".join(f"- {q}" for q in queries)

    llm = init_chat_model(
        settings.llm_model,
        api_key=settings.openai,
        temperature=0.2,
        timeout=60,
        max_tokens=800,
    )

    system_prompt = prototype_report_prompt.format(
        topic=topic,
        report_organization=report_organization,
        context=context,
        feedback=feedback,
        sections=sections
    )

    resp = llm.invoke([SystemMessage(content=system_prompt)])
    text = resp.content.strip()

    data = json.loads(text)
    sections = data["sections"]

    # content는 항상 빈 문자열로 정규화
    for s in sections:
        s["content"] = ""

    return {**state, "sections": sections}
