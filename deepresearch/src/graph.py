# src/graph.py
from langgraph.graph import StateGraph, START, END

from src.state import ResearchState
from src.agents.supervisor import supervisor_node
from src.agents.planner import plan_subqueries
from src.agents.retriever import tavily_search
from src.agents.verifier import verify_results
from src.agents.writer import build_markdown_report
from src.agents.report_reviewer import report_reviewer_node


def planner_node(state: ResearchState) -> ResearchState:
    return {"sub_queries": plan_subqueries(state["question"])}


def retriever_node(state: ResearchState) -> ResearchState:
    return {"search_results": tavily_search(state.get("sub_queries", []))}


def verifier_node(state: ResearchState) -> ResearchState:
    return {"search_results": verify_results(state.get("search_results", []))}


def writer_node(state: ResearchState) -> ResearchState:
    report = build_markdown_report(state["question"], state.get("search_results", []))
    return {"report_markdown": report}

def should_continue(state: ResearchState) -> str:
    if state.get("is_complete") or state.get("need_clarification"):
        return "end"
    return "continue"


def build_graph() -> StateGraph:
    g = StateGraph(ResearchState)

    g.add_node("supervisor", supervisor_node)
    g.add_node("planner", planner_node)
    g.add_node("retriever", retriever_node)
    g.add_node("verifier", verifier_node)
    g.add_node("writer", writer_node)
    g.add_node("reviewer", report_reviewer_node)


    g.add_edge(START, "supervisor")
    
    g.add_conditional_edges(
        "supervisor", 
        should_continue,
        {
            "continue": "planner",
            "end": END
        }
    )

    g.add_edge("planner", "retriever")
    g.add_edge("retriever", "verifier")
    g.add_edge("verifier", "writer")
    g.add_edge("writer", "reviewer")
    g.add_edge("reviewer", END)

    return g.compile()



__all__ = ["build_graph"]
