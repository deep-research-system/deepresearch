# src/api/stream.py
from __future__ import annotations

from typing import Any, Dict, Iterator, Callable, Iterable, Tuple

from fastapi.responses import StreamingResponse

from src.utils.sse import sse
from src.api.handlers.clarify import handle_clarify

Event = Tuple[str, Dict[str, Any]]  # (event_name, payload)
Handler = Callable[[Dict[str, Any]], Iterable[Event]]

## 노드 이름과 핸들러 매핑
HANDLERS: Dict[str, Handler] = {
    "clarify": handle_clarify,
    # 노드 추가 시 여기에만 등록하면 됨
    # "write_research_brief": handle_brief,
    # "research_supervisor": handle_supervisor,
    # "final_report_generation": handle_final,
}

# 스트림 청크 정규화
def _normalize_chunk(chunk: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """
    stream_mode="updates" chunk는 보통 {"node_name": {...update...}} 형태.
    이를 (node_name, update)로 정규화한다.
    """
    if not isinstance(chunk, dict) or not chunk:
        return "unknown", {"raw": chunk}

    node = next(iter(chunk.keys()))
    update = chunk[node]
    if not isinstance(update, dict):
        update = {"value": update}
    return node, update

# LangGraph 스트리밍 응답
def stream_graph(graph, state_in: Dict[str, Any]) -> StreamingResponse:
    """
    LangGraph 실행 결과를 SSE로 스트리밍한다.
    - 공통 이벤트(start, node_update, end, error)는 여기서 처리
    - 노드별 UI 이벤트는 handlers에서 처리
    """
    # 이벤트 생성기
    def event_generator() -> Iterator[str]:
        # 1) 시작
        yield sse("start", {"message": "딥리서치 시작"})

        try:
            # 2) LangGraph updates 스트림
            for chunk in graph.stream(state_in, stream_mode="updates"):
                node, update = _normalize_chunk(chunk)

                # 공통: 노드 업데이트(진행상황)
                yield sse(
                    "node_update",
                    {
                        "node": node,
                        "update": update,          # 디버깅/로그용
                        "message": f"[{node}] 처리 중",
                    },
                )

                # 노드별: 필요 시 추가 이벤트(assistant 메시지 등)
                handler = HANDLERS.get(node)
                if handler:
                    for event_name, payload in handler(update):
                        yield sse(event_name, payload)

            # 3) 종료
            yield sse("end", {"message": "딥리서치 종료"})

        except Exception as e:
            # 에러
            yield sse(
                "error",
                {
                    "type": type(e).__name__,
                    "message": str(e),
                },
            )
            # 에러 후 종료 이벤트도 보내는 편이 프론트 처리에 유리
            yield sse("end", {"message": "딥리서치 종료(에러)"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
