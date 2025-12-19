"""연구 문서를 종합하고 요약하는 역할을 하는 에이전트.

이 모듈은 여러 정보를 조합하여 일관된 서사나 구조화된 요약을 만드는 기본 틀을 제공한다.
완전한 시스템에서는 언어 모델을 사용하여 검색된 문서의 인용을 바탕으로 간결하면서도 포괄적인 답변을 생성한다.
현재는 데모 목적으로 각 결과의 제목과 스니펫을 단순히 이어 붙인다.
"""

from typing import List, Dict, Any


def synthesize(search_results: List[Dict[str, Any]]) -> str:
    """합성을 위한 임시 함수.

    Args:
        search_results: 검증된 검색 결과 목록. 각 결과는 적어도 제목과 (선택적으로) 스니펫이나 내용 필드를 포함한다.

    Returns:
        모든 결과의 제목을 이어 붙인 단순 문자열을 반환한다. 원하는 LLM이나 요약 기법을 사용하여 실제 요약 로직으로 교체하라.
    """
    lines = []
    for block in search_results:
        for result in block.get("results", []):
            title = result.get("title", "Untitled")
            snippet = result.get("content", "") or result.get("snippet", "")
            lines.append(f"- {title}\n  {snippet}")
    return "\n".join(lines)


__all__ = ["synthesize"]