from __future__ import annotations
from typing import Any, Dict, Iterable, Tuple

Event = Tuple[str, Dict[str, Any]]

def handle_clarify(update: Dict[str, Any]) -> Iterable[Event]:
    if update.get("type") == "assistant_text":
        content = (update.get("content", "") or "")
        if "NO_QUESTION" in content:
            return []
        yield ("assistant", {"type": "assistant_text", "content": content})
        return

    qs = update.get("clarifying_questions", None) or update.get("questions", None)
    if isinstance(qs, list) and qs:
        yield ("assistant", {"type": "clarify_questions_done", "questions": qs})
        return

    fq = update.get("final_question", None)
    if isinstance(fq, str) and fq.strip():
        yield ("assistant", {"type": "final_question", "question": fq.strip()})
        return

    if "need_clarification" in update:
        if update["need_clarification"]:
            yield ("assistant", {"type": "clarify_questions_done", "questions": []})
        else:
            yield ("assistant", {"type": "final_question", "question": ""})
        return

    return []
