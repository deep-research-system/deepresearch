from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple

Event = Tuple[str, Dict[str, Any]]  # (event_name, payload)


def handle_node_update(node: str, update: Dict[str, Any]) -> Iterable[Event]:
    if node == "clarify":
        # 1) 스트리밍 텍스트 (State 기반: assistant_text 필드)
        if "assistant_text" in update:
            content = update.get("assistant_text") or ""
            if content and "NO_QUESTION" not in content:
                yield ("assistant", {"type": "assistant_text", "content": content})
            return

        # 2) 추가질문 리스트(프론트 저장용) 1회 전달
        if update.get("need_clarification") is True and update.get("clarifying_questions"):
            qs = update.get("clarifying_questions") or []
            if qs:
                yield ("assistant", {"type": "clarify_questions", "questions": qs})
            return

        # 3) 최종 질문 1회 전달
        if "final_question" in update:
            fq = (update.get("final_question") or "").strip()
            if fq:
                yield ("assistant", {"type": "final_question", "question": fq})
            return

        return

    if node == "subquery":
        subqs = update.get("sub_queries") or []
        if subqs:
            yield ("assistant", {"type": "subqueries_done", "sub_queries": subqs})
        return

    return
