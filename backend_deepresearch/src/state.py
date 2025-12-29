from typing import TypedDict, List, Annotated


class BaseState(TypedDict, total = False):
    question: Annotated[str, "기준이될 사용자 입력"]
    messages: Annotated[List[str], "대화 히스토리"]


class ClarifyState(TypedDict, total = False):
    error_messages: Annotated[str, "잘못된 질문 입력에대한 LLM의 답변"]
    need_addition_questions: Annotated[bool, "추가 질문 필요 여부"]
    qna_ment: Annotated[str, "추가질문 안내문구"]
    addition_questions: Annotated[List[str], "추가질문 리스트"]
    addition_questions_answers: Annotated[List[str], "사용자가 답한 추가질문"]
    final_question: Annotated[str, "확정된 최종 질문"]


class SubqueryState(TypedDict):
    subqueries: Annotated[List[str], "웹검색용 질문들(서브쿼리)"]


class ResearchState(BaseState, ClarifyState, SubqueryState, total=False):
    pass