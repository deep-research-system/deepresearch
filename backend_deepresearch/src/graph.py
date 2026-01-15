from langgraph.graph import StateGraph, END
from src.state import PlannerState
from src.agents.subquery import generate_queries
from src.agents.prototype_report import plan_sections

def after_plan_sections(state: PlannerState) -> str:
    # 승인 전: 종료 -> 프론트에서 피드백 받기
    if state.get("approved") is True:
        return "end"  # 나중에 "search"로 바꿀 자리
    return "end"

def build_graph():
    g = StateGraph(PlannerState)
    g.add_node("plan_queries", generate_queries)
    g.add_node("plan_sections", plan_sections)

    g.set_entry_point("plan_queries")
    g.add_edge("plan_queries", "plan_sections")

    g.add_conditional_edges("plan_sections", after_plan_sections, {"end": END})

    return g.compile()

graph = build_graph()
