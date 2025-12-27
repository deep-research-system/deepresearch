from __future__ import annotations

from typing import Any, Dict, Iterator, Tuple
import json

from fastapi.responses import StreamingResponse

from src.handler.definition_handle import handle_node_update

Event = Tuple[str, Dict[str, Any]]  # (event_name, payload)


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _normalize_chunk(chunk: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """
    LangGraph stream_mode="updates" 결과는 보통 {"node_name": {...update...}} 형태.
    """
    if not isinstance(chunk, dict) or not chunk:
        return "unknown", {"raw": chunk}

    node = next(iter(chunk.keys()))
    update = chunk.get(node) or {}
    if not isinstance(update, dict):
        update = {"raw": update}
    return node, update


def _status_message_for(node: str, state_in: Dict[str, Any]) -> str:
    if node == "clarify":
        if state_in.get("clarifying_answers"):
            return "최종 질문 생성중..."
        return "질문분석중..."
    if node == "subquery":
        return "서브쿼리 생성중..."
    return f"{node} 처리중..."


def stream_graph(graph, state_in: Dict[str, Any]) -> StreamingResponse:
    def event_generator() -> Iterator[str]:
        try:
            yield sse("start", {"message": "딥리서치 시작"})

            for chunk in graph.stream(state_in, stream_mode="updates"):
                node, update = _normalize_chunk(chunk)

                # clarify의 assistant_text 스트리밍 중에는 상태 메시지 섞이지 않게 억제
                if not (node == "clarify" and "assistant_text" in update):
                    yield sse("node_update", {"message": _status_message_for(node, state_in)})

                for event_name, payload in (handle_node_update(node, update) or []):
                    yield sse(event_name, payload)

            yield sse("end", {"message": "딥리서치 종료"})

        except Exception as e:
            yield sse("error", {"type": type(e).__name__, "message": str(e)})
            yield sse("end", {"message": "딥리서치 종료(에러)"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
