from typing import Any, Dict, Iterable, Tuple
Event = Tuple[str, Dict[str, Any]]  # (event_name, payload)


def handle_node_update(node: str, update: Dict[str, Any]) -> Iterable[Event]:
    if node == "clarify":
        # 1. 이상한 입력 -> 다시 입력하라는 메세지
        if "error_messages" in update:
            error_messages = update.get("error_messages")
            if error_messages:
                yield ("llm", {"type": "error_messages", "content": error_messages})
            return


        # 2. 추가질문 할필요 없음 —> 최종 검색어
        if update.get("need_addition_questions") is False:
            final_question = update.get("final_question")
            if final_question:
                yield ("llm", {"type": "final_question", "question": final_question})
            return


        # 1) 추가질문 할필요 있음 —> 안내 멘트 + 추가질문 리스트
        if update.get("need_addition_questions") is True:
            qna_ment = update.get("qna_ment")
            addition_questions = update.get("addition_questions")
            if qna_ment:
                yield ("llm", {"type": "qna_ment", "content": qna_ment})
            if addition_questions:
                yield ("llm", {"type": "addition_questions", "questions": addition_questions})
            return









    # (미사용) 서브쿼리 이벤트
    # if node == "subquery":
    #     subqs = update.get("subqueries") or []
    #     if subqs:
    #         yield ("assistant", {"type": "subqueries_done", "subqueries": subqs})
    #     return





