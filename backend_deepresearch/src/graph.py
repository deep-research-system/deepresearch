from __future__ import annotations

from langgraph.graph import StateGraph, END
from src.state import ResearchState
from src.agents.clarify import clarify
from src.agents.subquery import subquery


def build_graph():
    g = StateGraph(ResearchState)
    g.add_node("clarify", clarify)
    g.add_node("subquery", subquery)

    g.set_entry_point("clarify")

    g.add_conditional_edges(
        "clarify",
        lambda s: "subquery" if not s.need_clarification else END,
        {"subquery": "subquery", END: END},
    )
    g.add_edge("subquery", END)
    return g.compile()
