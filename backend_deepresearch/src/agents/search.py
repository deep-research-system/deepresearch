# src/nodes/search.py
from tavily import AsyncTavilyClient
import asyncio
from configuration import settings
from src.state import SubqueryState, SearchState


tavily = AsyncTavilyClient(api_key=settings.tavily)


async def search_node(state: SubqueryState) -> SearchState:
    """
    서브쿼리 → 웹 검색 → URL 수집
    """
    subqueries = state.get("subqueries")
    search_results = []

    tasks = [
        tavily.search(
            query,
            max_results=1,
            include_raw_content=False,
            topic="general")
        for query in subqueries]
    
    responses = await asyncio.gather(*tasks)


    for query, resp in zip(subqueries, responses):
        for item in resp.get("results", []):
            search_results.append({
                "query": query,
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("content"),
                "score": item.get("score"),
                "source": "tavily",
            })

    return {"search_results": search_results}