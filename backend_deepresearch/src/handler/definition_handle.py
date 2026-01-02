from typing import Any, Dict, Iterable, Tuple
Event = Tuple[str, Dict[str, Any]]  # (event_name, payload)


def handle_node_update(node: str, update: Dict[str, Any]) -> Iterable[Event]:
    if node == "clarify_first":
        # 1. 비정상 입력 -> 다시 입력하라는 메세지
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

        # 3. 추가질문 할필요 있음 —> 안내 멘트 + 추가질문 리스트
        if update.get("need_addition_questions") is True:
            qna_ment = update.get("qna_ment")
            addition_questions = update.get("addition_questions")
            if qna_ment:
                yield ("llm", {"type": "qna_ment", "content": qna_ment})
            if addition_questions:
                for add_questions in addition_questions:
                    yield ("llm", {"type": "addition_questions", "questions": add_questions})
            return
    
    elif node == "clarify_answer":
        # 4-1. 추가질문 답변 충분 -> 최종 검색
        if update.get("answers_sufficient") is True:
            final_question = update.get("final_question")
            if final_question:
                yield ("llm", {"type": "final_question", "question": final_question})
            return

        # 4-2. 추가질문 답변 불충분 -> 재질문 멘트 + 추가질문
        if update.get("answers_sufficient") is False:
            qna_ment = update.get("qna_ment")
            addition_questions = update.get("addition_questions")
            if qna_ment:
                yield ("llm", {"type": "qna_ment", "content": qna_ment})
            if addition_questions:
                for add_questions in addition_questions:
                    yield ("llm", {"type": "addition_questions", "questions": add_questions})
            return
        
    elif node == "subquery":
        for q in update.get("subqueries", []):
            yield ("llm", {"type": "subqueries", "query": q})
        return
        
    elif node == "search":
        for result in update.get("search_results", []):
            yield ("llm", {
                "type": "search_results",   # 혹은 "search_result" 단수로 통일해도 됨
                "result": {
                    "title": result.get("title"),
                    "url": result.get("url"),
                    "query": result.get("query"),
                }
            })
        return