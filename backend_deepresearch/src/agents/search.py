from tavily import AsyncTavilyClient
import asyncio
import trafilatura, httpx

from configuration import settings
from src.state import SubqueryState, SearchState

tavily = AsyncTavilyClient(api_key=settings.tavily)

async def search_node(state: SubqueryState) -> SearchState:
    subqueries = state.get("subqueries") or []
    final = []

    # 1. 웹 검색 (병렬)
    search_tasks = []
    for sub_q in subqueries:
        search_tasks.append(tavily.search(sub_q, max_results=3, topic="general"))
    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    # 2. URL 크롤링 (병렬)
    crawl_tasks = []
    timeout = httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0)

    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        for search_r in search_results:
            if isinstance(search_r, Exception) or search_r is None:
                continue

            for result in (search_r.get("results") or []):
                url = result.get("url")
                if url:
                    crawl_tasks.append(client.get(url))

        contents = await asyncio.gather(*crawl_tasks, return_exceptions=True)

    count = 0
    for sub_q, search_r in zip(subqueries, search_results):
        if isinstance(search_r, Exception) or search_r is None:
            continue

        for item in (search_r.get("results") or []):
            resp = contents[count]
            count += 1

            if isinstance(resp, Exception):
                continue

            url = item.get("url")
            html = resp.text
            content = trafilatura.extract(html)

            final.append({
                "query": sub_q,
                "title": item.get("title"),
                "url": url,
                "content": content,
                "score": item.get("score"),
                "source": "tavily",
            })

    return {"search_results": final}
