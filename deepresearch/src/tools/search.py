"""딥리서치를 위한 검색 유틸리티.

현재 이 모듈은 Tavily 검색 API에 대한 간단한 래퍼이다.
빙, 구글, 위키피디아 등 다른 검색 제공자를 통합하고 싶다면 이곳에 추가 함수들을 구현하고,
리트리버에서 선택할 수 있게 하면 된다.
"""

from typing import List, Dict, Any
from tavily import TavilyClient

from configuration import settings


def tavily_search(query: str, max_results: int | None = None) -> List[Dict[str, Any]]:
    """Tavily API를 사용하여 검색을 수행한다.

    Args:
        query: 검색 쿼리 문자열.
        max_results: 반환할 결과의 최대 개수(선택). None이면 ``settings.max_results_per_query``값을 사용한다.

    Returns:
        최소한 'title'과 'url' 키를 포함하는 결과 사전의 목록을 반환한다.
    """
    if not settings.tavily_api_key:
        raise RuntimeError(
            "TAVILY_API_KEY가 설정되어 있지 않습니다. .env를 확인하세요."
        )
    client = TavilyClient(api_key=settings.tavily_api_key)
    res = client.search(
        query=query,
        max_results=max_results or settings.max_results_per_query,
        include_answer=False,
        include_raw_content=False,
        include_images=False,
    )
    return res.get("results", [])


__all__ = ["tavily_search"]