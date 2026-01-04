import json
from typing import Any, Dict

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

from configuration import settings
from src.state import ClarifyState
from src.prompts.prompts import subquery_prompt

def llm_subquery():
    return init_chat_model(
        settings.llm_model,
        api_key=settings.openai,
        temperature=0.6)
llm_sub = llm_subquery()

def subquery(state: ClarifyState) -> Dict[str, Any]:
    final_question = (state.get("final_question") or "").strip()

    # final_question이 비어있는 경우 예외 처리
    if not final_question:
        return {
            "subqueries": [],
            "error_messages": "final_question이 비어있어 subquery를 생성할 수 없습니다."
        }
    
    # LLM 호출
    llm_response = llm_sub.invoke([
        SystemMessage(content=subquery_prompt),
        HumanMessage(content=f'최종 질문: "{final_question}"')
    ])
    llm_raw = llm_response.content

    try:
        llm_json = json.loads(llm_raw)
    except json.JSONDecodeError:
        return {
            "subqueries": [],
            "error_messages": f"subquery JSON 파싱 실패: {llm_raw}"
        }
    
    subqueries = llm_json.get("subqueries")

    if not isinstance(subqueries, list):
        return {
            "subqueries": [],
            "error_messages": f'subqueries가 리스트가 아닙니다: {llm_raw}'
        }

    cleaned = []
    for q in subqueries:
        if isinstance(q, str):
            q = q.strip()
            if q:
                cleaned.append(q)

    if not cleaned:
        return {
            "subqueries": [],
            "error_messages": f"subqueries가 비어있거나 유효한 문자열이 없습니다: {llm_raw}"
        }

    return {"subqueries": cleaned}
    



