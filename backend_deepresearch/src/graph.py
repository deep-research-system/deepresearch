from __future__ import annotations
from langgraph.graph import StateGraph, END
from src.state import ResearchState
from src.agents.clarify import clarify

def build_graph():
    g = StateGraph(ResearchState)
    g.add_node("clarify", clarify)
    g.set_entry_point("clarify")
    g.add_edge("clarify", END)
    return g.compile()
