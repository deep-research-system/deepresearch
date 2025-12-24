
from __future__ import annotations
from typing import Any, Dict, Iterable, Tuple


Event = Tuple[str, Dict[str, Any]]  # (event_name, payload)


def handle_subquery(update: Dict[str, Any]) -> Iterable[Event]:
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

    # 2) subquery 종료 후 결과 이벤트
    if "sub_queries" in update:
        yield (
            "assistant",
            {
                "type": "subqueries_done",
                "sub_queries": update.get("sub_queries", []),
            },
        )
