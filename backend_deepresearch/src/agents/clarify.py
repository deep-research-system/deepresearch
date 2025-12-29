import json
from typing import Any, Dict

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

from configuration import settings
from src.state import BaseState, ClarifyState
from src.prompts.prompts import clarify_question_prompt

def llm_set():
    return init_chat_model(
        settings.llm_model,
        api_key=settings.openai,
        temperature=settings.temperature)
llm = llm_set()

### 여기까지 건들지말라고 밑으로만 생성하라고



def clarify(state: BaseState):
    """
    1단계 : 질문이 완전 이상한게 들어옴 -> 잘못된 입력입니다. 다시입력해주세요. 출력 후 끝 냄
    2단계 : 추가질문 여부 확인 / 추가질문 출력
    """
    question = state.get("question")

    llm_answer = llm.invoke([
        SystemMessage(content=clarify_question_prompt),
        HumanMessage(content=question)
    ])
    llm_raw = llm_answer.content

    try:
        llm_json = json.loads(llm_raw)
    except:
        return {"error_messages" : llm_raw}


    if llm_json.get("need_addition_questions") is False:
        return{"need_addition_questions" :False,
               "final_question" : question}
    
    if llm_json.get("need_addition_questions") is True:
        return {"need_addition_questions" : True,
                "qna_ment" : llm_json["qna_ment"],
                "addition_questions" : llm_json["addition_questions"]}