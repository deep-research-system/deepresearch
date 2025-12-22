from fastapi.responses import StreamingResponse
import json

# Server-Sent Events (SSE) 유틸리티 함수
def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
