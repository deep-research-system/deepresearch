"""외부 소스에서 문서를 가져오는 역할을 하는 에이전트.

이 모듈은 웹 검색 API(예: Tavily) 호출을 감싸며 각 서브 쿼리에 대한 결과를 반환한다.
미래에는 크롤링 콘텐츠를 포함하거나 여러 검색 엔진을 사용하는 등으로 확장할 수 있다.
"""

from typing import List, Dict, Any
from tavily import TavilyClient

from configuration import settings


def tavily_search(sub_queries: List[str]) -> List[Dict[str, Any]]:
    """Tavily API를 사용하여 각 서브 쿼리에 대한 웹 검색을 수행한다.

    Args:
        sub_queries: 플래너가 생성한 검색 쿼리 목록.

    Returns:
        각 서브 쿼리와 이에 대응하는 검색 결과를 담은 사전들의 목록을 반환한다.
        각 결과는 최소한 ``title``과 ``url`` 키를 포함하는 사전이며, 추가 메타데이터는 API에 따라 제공될 수 있다.
    """
    if not settings.tavily_api_key:
        raise RuntimeError(
            "TAVILY_API_KEY가 설정되어 있지 않습니다. .env를 확인하세요."
        )
    client = TavilyClient(api_key=settings.tavily_api_key)
    aggregated: List[Dict[str, Any]] = []
    for q in sub_queries:
        res = client.search(
            query=q,
            max_results=settings.max_results_per_query,
            include_answer=False,
            include_raw_content=False,
            include_images=False,
        )
        aggregated.append({
            "query": q,
            "results": res.get("results", []),
        })
    return aggregated


__all__ = ["tavily_search"]