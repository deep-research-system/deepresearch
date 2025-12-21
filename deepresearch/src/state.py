from typing import Annotated, Optional, TypedDict, List, Dict, Any
from langgraph.graph.message import add_messages


class ResearchState(TypedDict, total=False):
    question: str
    active_mode: str  # 추가: "chat" | "research"
    messages: Annotated[list, add_messages]  #  추가: 대화 기록
    is_complete: Optional[bool]  #  추가: 조기 종료 플래그

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
