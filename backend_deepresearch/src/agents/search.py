# src/nodes/search.py
from __future__ import annotations

import os, asyncio
from typing import Any, TypedDict, List
from tavily import AsyncTavilyClient
from dotenv import load_dotenv
from src.state import SubqueryState, SearchState, SearchResult
 
load_dotenv()


# Tavily 클라이언트 생성 함수
def _get_tavily_client() -> AsyncTavilyClient:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY 환경변수가 설정되어 있지 않습니다.")
    return AsyncTavilyClient(api_key=api_key)


async def _tavily_search_many(
    queries: List[str],
    max_results: int = 3,
    topic: str = "general",
) -> List[dict[str, Any]]:
    """
    여러 쿼리를 Tavily로 병렬 검색하고, 쿼리별 응답(dict)을 리스트로 반환.
    (요약/평가/재시도 없음)
    """
    client = _get_tavily_client()

    # 1) 요청 task 만들기
    tasks = [
        client.search(
            q,
            max_results=max_results,
            include_raw_content=False,  # Search-only: 본문 수집하지 않음
            topic=topic,
        )
        for q in queries
    ]
    # 2) 동시에 병렬 실행
    # gather(): *tasks가 완료될 때까지 실행 결과를 [result1, result2, ...] 형태로 반환
    # return_exceptions=True: 예외 발생해도 멈추지 않고 결과에 예외 객체 포함
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    # 3) 성공한 것만 out에 쌓기
    out: List[dict[str, Any]] = []
    for q, resp in zip(queries, responses):
        #  쿼리검색 실패시 넘어가서 진행
        if isinstance(resp, Exception):
            continue
        #  tavily 응답이 dict일시 정상처리
        if isinstance(resp, dict):
            resp.setdefault("query", q)
            out.append(resp)
    return out


async def search_node(state: SubqueryState) -> SearchState:
    """ LangGraph Search 노드 (Search-only)
    - 입력: state["subqueries"]
    - 출력: {"search_result": List[SearchResult]}
    - URL 기준 dedupe (첫 등장 query 유지)
    """
    subqueries = state.get("subqueries") or []
    if not isinstance(subqueries, list):
        subqueries = []

    # 문자열 쿼리, 앞뒤 공백제거
    queries = [q.strip() for q in subqueries if isinstance(q, str) and q.strip()]
    if not queries:
        return {"search_results": []}

    # 1) 병렬 검색
    responses = await _tavily_search_many(queries, max_results=3, topic="general")

    # 2) 같은 url은 한번만 저장, 먼저 등장한 쿼리결과 유지지
    unique_by_url: dict[str, SearchResult] = {}

    for resp in responses:
        q = resp.get("query")
        tavily_results   = resp.get("results") or []
        if not isinstance(tavily_results, list):
            continue

        for item in tavily_results:
            if not isinstance(item, dict):
                continue

            url = str(item.get("url") or "").strip()
            if not url:
                continue

            # dedupe: URL이 이미 있으면 스킵(첫 등장 query 유지)
            if url in unique_by_url:
                continue
            #  URL결과를 SearchResult로 변환
            sr: SearchResult = {
                "query": str(q or ""),
                "title": str(item.get("title") or ""),
                "url": url,
                # Tavily 결과의 content/snippet/description 중 가능한 걸 snippet로
                "snippet": (
                    item.get("content")
                    or item.get("snippet")
                    or item.get("description")
                    or None
                ),
                "score": item.get("score") if isinstance(item.get("score"), (int, float)) else None,
                "source": "tavily",
            }
            unique_by_url[url] = sr
        print("[SEARCH_NODE] called. subqueries=", state.get("subqueries"))

    return {"search_results": list(unique_by_url.values())}