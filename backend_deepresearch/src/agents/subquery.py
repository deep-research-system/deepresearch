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
llm = llm_subquery()

def subquery(state: ClarifyState):
    final_question = state.get("final_question")
    
    # LLM 호출
    llm_answer = llm.invoke([
        SystemMessage(content=subquery_prompt),
        HumanMessage(content=f'최종 질문: "{final_question}"')
    ])
    
    llm_raw = llm_answer.content
    llm_json = json.loads(llm_raw)

    subqueries = llm_json.get("subqueries")
    return {"subqueries": subqueries}
