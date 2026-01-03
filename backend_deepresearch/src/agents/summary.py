import json
from typing import Any, Dict, List, Optional

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

from configuration import settings
from src.state import ResearchState, DocSummary, SearchResult
from src.prompts.prompts import doc_summary_prompt


def llm_summary():
    return init_chat_model(
        settings.llm_model,
        api_key=settings.openai,
        temperature=0.2,
        timeout=60,
        max_tokens=600,
    )

# score 타입 확인
def _safe_float(x: Any) -> Optional[float]:
    return float(x) if isinstance(x, (int, float)) else None

# 프롬프트 출력 파싱/검증증
def _parse_doc_summary_json(raw: str) -> Dict[str, Any]:
    # 공백이면 기본값
    t = (raw or "").strip()
    if not t:
        return {"summary": "", "bullets": [], "reliability_notes": ""}

    # json 파싱
    try:
        obj = json.loads(t)
    except Exception:
        # JSON이 아니면 그대로 summary로 폴백
        return {"summary": t, "bullets": [], "reliability_notes": "JSON 파싱 실패(폴백)"}

    if not isinstance(obj, dict):
        return {"summary": t, "bullets": [], "reliability_notes": "JSON 형식 불일치(폴백)"}

    summary = obj.get("summary") or ""
    bullets = obj.get("bullets") or []
    notes = obj.get("reliability_notes") or ""

    if not isinstance(bullets, list):
        bullets = []

    bullets_clean = []
    for b in bullets:
        if isinstance(b, str):
            b = b.strip()
            if b:
                bullets_clean.append(b)

    return {
        "summary": str(summary).strip(),
        "bullets": bullets_clean[:5],
        "reliability_notes": str(notes).strip(),
    }

# LLM에 줄 문서 입력 텍스트 만들기
def _build_llm_input(r: SearchResult) -> str:
    # snippet이 None이면 빈 문자열 처리
    snippet = r.get("snippet") or ""
    return (
        f'query: {r.get("query") or ""}\n'
        f'title: {r.get("title") or ""}\n'
        f'url: {r.get("url") or ""}\n'
        f'snippet: {snippet}\n'
    )


async def summary_node(state: ResearchState):
    """
    - 입력: state["search_results"]
    - 출력: state["doc_summaries"] 누적 + 문서별 SSE yield
    """
    search_results: List[Dict[str, Any]] = state.get("search_results") or []
    if not isinstance(search_results, list) or not search_results:
        state["doc_summaries"] = []
        yield {"doc_summaries": []}
        return

    llm = llm_summary()

    doc_summaries: List[DocSummary] = state.get("doc_summaries") or []
    if not isinstance(doc_summaries, list):
        doc_summaries = []

    for r in search_results:
        if not isinstance(r, dict):
            continue

        # LLM 호출
        llm_input = _build_llm_input(r)
        resp = await llm.ainvoke([
            SystemMessage(content=doc_summary_prompt),
            HumanMessage(content=llm_input),
        ])
        raw = getattr(resp, "content", "") or ""
        parsed = _parse_doc_summary_json(raw)

        item: DocSummary = {
            "query": str(r.get("query") or ""),
            "title": str(r.get("title") or ""),
            "url": str(r.get("url") or ""),
            "source": str(r.get("source") or ""),
            "score": _safe_float(r.get("score")),
            "summary": parsed["summary"],
            "bullets": parsed["bullets"],
            "reliability_notes": parsed["reliability_notes"] or None,
        }

        doc_summaries.append(item)
        state["doc_summaries"] = doc_summaries

        # SSE: 문서 1개 요약 완료마다 순차 전달
        yield {"doc_summary": item}

    # SSE: 전체 리스트도 마지막에 한번 전달
    yield {"doc_summaries": doc_summaries}
