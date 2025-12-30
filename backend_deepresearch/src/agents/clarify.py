import json
from typing import Any, Dict

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

from configuration import settings
from src.state import BaseState, ClarifyState
from src.prompts.prompts import clarify_question_prompt, clarify_answer_judge_prompt

def llm_set():
    return init_chat_model(
        settings.llm_model,
        api_key=settings.openai,
        temperature=settings.temperature)
llm = llm_set()

### 여기까지 건들지말라고 밑으로만 생성하라고



def clarify_first_question(state: BaseState):
    """
    1단계 : 질문이 완전 이상한게 들어옴 -> 잘못된 입력입니다. 다시입력해주세요. 출력 후 끝 냄
    2단계 : 추가질문 여부 확인 / 추가질문 출력
    """
    question = state.get("question")

    llm_answer = llm.invoke([
        SystemMessage(content=clarify_question_prompt),
        HumanMessage(content=question)
    ])
    llm_answer_raw = llm_answer.content

    try:
        llm_json = json.loads(llm_answer_raw)
    except:
        return {"error_messages" : llm_answer_raw}


    if llm_json.get("need_addition_questions") is False:
        return{"need_addition_questions" :False,
               "final_question" : llm_json["final_question"]}
    
    if llm_json.get("need_addition_questions") is True:
        return {"need_addition_questions" : True,
                "qna_ment" : llm_json["qna_ment"],
                "addition_questions" : llm_json["addition_questions"]}
    
    

def clarify_add_answer(state: BaseState):
    """
    3단계 : 추가질문에 대한 답변 판단 후 최종 검색어 생성
    - 답변이 부족하면 다시 재질문

    """
    question = state.get("question")
    addition_questions = state.get("addition_questions")
    addition_questions_answers = state.get("addition_questions_answers")

    llm_add_answer= llm.invoke([
        SystemMessage(content=clarify_answer_judge_prompt),
        HumanMessage(content=f"원 질문: {question}\n추가질문: {addition_questions}\n사용자 답변: {addition_questions_answers}")])
    
    llm_add_answer= llm_add_answer.content
    llm_json = json.loads(llm_add_answer)

    if llm_json.get("answers_sufficient") is True:
        return {"answers_sufficient": True,
                "final_question": llm_json.get("final_question")}
    
    return {"answers_sufficient": False,
            "qna_ment": llm_json.get("qna_ment"),
            "addition_questions": addition_questions}