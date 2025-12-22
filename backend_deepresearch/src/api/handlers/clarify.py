# src/api/handlers/clarify.py
from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple

Event = Tuple[str, Dict[str, Any]]  # (event_name, payload)


def handle_clarify(update: Dict[str, Any]) -> Iterable[Event]:
    """
    clarify 노드의 update(dict)를 받아서, UI에 보여줄 SSE 이벤트로 변환한다.
    """

    # 진행 메시지(선택): clarify가 어떤 결론을 냈는지
    if update.get("need_clarification"):
        yield (
            "assistant",
            {
                "type": "clarify_questions",
                "content": "추가로 몇 가지 확인할게요.",
                "questions": update.get("clarifying_questions", []),
            },
        )
    else:
        fq = update.get("final_question")
        yield (
            "assistant",
            {
                "type": "final_question",
                "content": fq,
            },
        )
        # 필요하면 여기서 바로 "assistant"로 최종 안내 메시지도 추가 가능
        yield (
            "assistant",
            {
                "type": "assistant_text",
                "content": f"명확화된 질문:\n{fq}",
            },
        )
