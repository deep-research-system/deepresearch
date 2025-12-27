from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ResearchState:
    question: str
    messages: list[dict[str, Any]] = field(default_factory=list)

    # 질문분석agent에서 다루는 필드 (clarify)
    assistant_text: str = ""
    need_clarification: bool = False
    clarifying_questions: list[str] = field(default_factory=list)
    clarifying_answers: list[str] = field(default_factory=list)
    final_question: str | None = None

    # 서브쿼리agent에서 다루는 필드 (subquery)
    sub_queries: list[str] = field(default_factory=list)