# src/api/handlers/clarify.py
from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple

Event = Tuple[str, Dict[str, Any]]  # (event_name, payload)


def handle_clarify(update: Dict[str, Any]) -> Iterable[Event]:
    # 1) 스트리밍 텍스트는 그대로 흘려보낸다
    if update.get("type") == "assistant_text":
        yield (
            "assistant",
            {
                "type": "assistant_text",
                "content": update["content"],
            },
        )
        return

    # 2) clarify 종료 후 상태 이벤트
    if "need_clarification" in update:
        if update["need_clarification"]:
            yield (
                "assistant",
                {
                    "type": "clarify_questions_done",
                    "questions": update.get("clarifying_questions", []),
                },
            )
        else:
            yield (
                "assistant",
                {
                    "type": "final_question",
                    "content": update.get("final_question"),
                },
            )
