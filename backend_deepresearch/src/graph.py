from langgraph.graph import StateGraph, END
from src.state import ResearchState
from src.agents.clarify import clarify


def build_graph():
    graph = StateGraph(ResearchState)

    # clarify 노드만 사용
    graph.add_node("clarify", clarify)

    # 시작점
    graph.set_entry_point("clarify")

    # clarify 실행 후 무조건 종료
    graph.add_edge("clarify", END)

    return graph.compile()
