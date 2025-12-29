# src/api/stream.py
import json
from typing import Any, Dict, Iterator, Tuple

from fastapi.responses import StreamingResponse

from src.handler.definition_handle import handle_node_update

Event = Tuple[str, Dict[str, Any]]  # (event_name, payload)


def sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _normalize_chunk(chunk: Any) -> tuple[str, Dict[str, Any]]:
    if not isinstance(chunk, dict) or not chunk:
        return "unknown", {"raw": chunk}

    node = next(iter(chunk.keys()))
    update = chunk.get(node)

    if isinstance(update, dict):
        return node, update
    return node, {"raw": update}


def _status_message_for(node: str, update: Dict[str, Any]) -> str:
    """
    ~~중... 표시
    """
    if node == "clarify":
        if "error_messages" in update:
            return "입력값 검증중..."
        if update.get("need_addition_questions") is True:
            return "추가 질문 생성중..."
        if update.get("need_addition_questions") is False:
            return "최종 질문 확정중..."
        return "질문 분석중..."

    # 필요하면 노드별 메시지를 여기서 확장
    return f"{node} 처리중..."


def start_graph(graph: Any, state: Dict[str, Any]) -> StreamingResponse:
    def event_generator() -> Iterator[str]:
        try:
            yield sse("start", {"message": "딥리서치 시작"})

            for chunk in graph.stream(state, stream_mode="updates"):
                node, update = _normalize_chunk(chunk)

                # 1) 상태 이벤트 (UI 상단 등)
                yield sse("node_update", {"message": _status_message_for(node, update)})

                # 2) 실제 메시지/이벤트 (handler.py 규격에 따름)
                for event_name, payload in (handle_node_update(node, update) or []):
                    yield sse(event_name, payload)

            yield sse("end", {"message": "딥리서치 종료"})

        except Exception as e:
            yield sse("error", {"type": type(e).__name__, "message": str(e)})
            yield sse("end", {"message": "딥리서치 종료(에러)"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
