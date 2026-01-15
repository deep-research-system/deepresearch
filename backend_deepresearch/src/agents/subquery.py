import json
from datetime import datetime
from typing import List, Optional

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

from configuration import settings, default_report_structure
from src.prompts.prompts import subquery_prompt
from src.state import PlannerState

def today() -> str:
    return datetime.now().strftime("%Y년 %m월 %d일")


def generate_queries(state: PlannerState, number_of_queries: int = 7):

    if state.get("queries"):
        return state
    # 1) 입력 정리/검증
    topic = state["topic"]
    report_organization = default_report_structure
    today_str = today()

    # 2) LLM 준비
    llm = init_chat_model(
        settings.llm_model,
        api_key=settings.openai,
        temperature=0.2,
        timeout=60,
        max_tokens=400,
    )

    # 3) 프롬프트 템플릿에 값 주입 (핵심)
    system_prompt = subquery_prompt.format(
        topic=topic,
        report_organization=report_organization,
        number_of_queries=number_of_queries,
        today=today_str,
    )

    # 4) 호출 (System만으로도 충분)
    llm_raw = llm.invoke([SystemMessage(content=system_prompt)])
    llm_text = llm_raw.content
    llm_json = json.loads(llm_text)
    queries = llm_json["queries"]

    return {**state, "queries":queries}