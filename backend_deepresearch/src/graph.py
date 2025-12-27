from langgraph.graph import StateGraph, END
from src.state import ResearchState
from src.agents.clarify import clarify
from src.agents.subquery import subquery


def build_graph():
    g = StateGraph(ResearchState)
    g.add_node("clarify", clarify)
    g.add_node("subquery", subquery)

    g.set_entry_point("clarify")

    # need_clarification=True이면 "이번 턴은 여기서 종료(사용자 답변 대기)" (clarify, end) or (clarify, subquery)
    g.add_conditional_edges(
        "clarify",
        lambda s: END if s.need_clarification else "subquery",
        {"subquery": "subquery", END: END},
    )

    g.add_edge("subquery", END)
    return g.compile()