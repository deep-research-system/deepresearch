"""마크다운 형식의 연구 보고서를 작성하는 역할을 하는 에이전트.

작성기는 원래 질문과 수집된 검색 결과를 받아 사람이 읽을 수 있는 마크다운 문서로 포맷한다.
초기 구현은 URL과 메타데이터를 제시하는 데 중점을 두며, 향후 단계에서는 크롤링된 내용, 분석, 인용 등을 포함할 수 있다.
"""

from typing import List, Dict, Any
from datetime import datetime


def build_markdown_report(
    question: str, search_results: List[Dict[str, Any]]
) -> str:
    """검색 결과로부터 간단한 마크다운 보고서를 구성한다.

    Args:
        question: 사용자의 원래 연구 질문.
        search_results: 리트리버가 반환한 결과 블록의 목록.

    Returns:
        마크다운 형식의 보고서를 담은 문자열을 반환한다.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: List[str] = []
    lines.append(f"# 딥리서치 결과")
    lines.append("")
    lines.append(f"- 질문: {question}")
    lines.append(f"- 생성 시각: {now}")
    lines.append("")
    lines.append("## 수집된 검색 결과(초안)")
    lines.append("")
    lines.append(">")
    lines.append("현재 버전은 URL 수집 중심 MVP입니다. 다음 단계에서 크롤링/검증/요약 노드를 추가합니다.")
    lines.append("")
    seen_urls: set[str] = set()
    idx = 1
    for block in search_results or []:
        q = block.get("query", "")
        results = block.get("results", [])
        if not results:
            continue
        lines.append(f"### 서브쿼리: {q}")
        lines.append("")
        for r in results:
            url = r.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            title = r.get("title", "Untitled")
            score = r.get("score", None)
            meta = []
            if score is not None:
                meta.append(f"score={score}")
            meta_str = f" ({', '.join(meta)})" if meta else ""
            lines.append(f"{idx}. **{title}**{meta_str}")
            lines.append(f"   - URL: {url}")
            idx += 1
        lines.append("")
    if idx == 1:
        lines.append("검색 결과가 비어 있습니다. (키/쿼리/네트워크 상태를 확인하세요.)")
    return "\n".join(lines)


__all__ = ["build_markdown_report"]