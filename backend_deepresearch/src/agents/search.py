# src/nodes/search.py
from tavily import AsyncTavilyClient
import asyncio
import trafilatura, httpx

from configuration import settings
from src.state import SubqueryState, SearchState

tavily = AsyncTavilyClient(api_key=settings.tavily)


async def search_node(state: SubqueryState) -> SearchState:
    subqueries = state.get("subqueries")
    final = []

    # 1. 웹 검색 (병렬)
    search_tasks = []
    for sub_q in subqueries:
        search_tasks.append(tavily.search(sub_q, max_results=3, topic="general"))
    search_results = await asyncio.gather(*search_tasks)


    # 2. URL 크롤링 (병렬)
    crawl_tasks = []
    async with httpx.AsyncClient() as client:
        for search_r in search_results:
            for result in search_r.get("results"):
                url = result.get("url")
                crawl_tasks.append(client.get(url))

        contents = await asyncio.gather(*crawl_tasks)


    count = 0
    for sub_q, search_r in zip(subqueries, search_results):
        for item in search_r.get("results"):
            url = item.get("url")
            html = contents[count].text
            content = trafilatura.extract(html)

            final.append({
                "query": sub_q,
                "title": item.get("title"),
                "url": url,
                "content": content,
                "score": item.get("score"),
                "source": "tavily",
            })

            count += 1

    return {"search_results": final}
