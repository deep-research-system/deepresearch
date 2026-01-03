from langgraph.graph import StateGraph, END
from src.state import ResearchState
from src.agents.clarify import clarify_first_question, clarify_add_answer
from src.agents.subquery import subquery
from src.agents.search import search_node
from src.agents.summary import summary_node

def start_to(state: ResearchState) -> str:
    # 2차 요청: 답변이 있으면 바로 답변판정 노드로
    if state.get("addition_questions_answers"):
        return "clarify_answer"
    # 1차 요청: 답변 없으면 원질문 판단 노드로
    return "clarify_first"

def to_subquery_or_end_from_first(state: ResearchState) -> str:
    fq = (state.get("final_question") or "").strip()
    if state.get("need_addition_questions") is False and fq:
        return "subquery"
    return "end"

def to_subquery_or_end_from_answer(state: ResearchState) -> str:
    fq = (state.get("final_question") or "").strip()
    if state.get("answers_sufficient") is True and fq:
        return "subquery"
    return "end"


def build_graph():
    graph = StateGraph(ResearchState)

    # router 노드(아무 것도 반환 안 해도 됨)
    graph.add_node("start", lambda state: state)
    graph.add_node("clarify_first", clarify_first_question)
    graph.add_node("clarify_answer", clarify_add_answer)
    graph.add_node("subquery", subquery)
    graph.add_node("search", search_node)
    graph.add_node("summary", summary_node)

    graph.set_entry_point("start")

    graph.add_conditional_edges(
        "start",
        start_to,
        {
            "clarify_first": "clarify_first",
            "clarify_answer": "clarify_answer",
        },)
    
    graph.add_conditional_edges(
        "clarify_first", 
        to_subquery_or_end_from_first, 
        {
            "subquery": "subquery",
            "end": END,
        },)

    graph.add_conditional_edges(
        "clarify_answer", 
        to_subquery_or_end_from_answer, 
        {
            "subquery": "subquery",
            "end": END,
        },)

    graph.add_edge("subquery", "search")
    graph.add_edge("search", "summary")
    graph.add_edge("summary", END)
    return graph.compile()
