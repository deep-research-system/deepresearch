from typing import TypedDict, List, Dict, Any


class ResearchState(TypedDict, total=False):
    question: str

    # Supervisor.py 관련 필드
    need_clarification: bool
    clarifying_questions: List[str]
    clarifying_answers: List[str]
    final_question: str

    # Planner / Retriever / ...
    sub_queries: List[str]
    search_results: List[Dict[str, Any]]
    report_markdown: str
    review_feedback: str


__all__ = ["ResearchState"]
