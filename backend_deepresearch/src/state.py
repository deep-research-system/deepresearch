from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ResearchState:
    question: str
    messages: list[dict[str, Any]] = field(default_factory=list)

    need_clarification: bool = False
    clarifying_questions: list[str] = field(default_factory=list)
    clarifying_answers: list[str] = field(default_factory=list)

    final_question: str | None = None
