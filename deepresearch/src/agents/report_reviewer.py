"""보고서 평가 에이전트.

최종 생성된 보고서를 검토하고 간단한 피드백을 제공한다. 현재 구현에서는 보고서를
그대로 전달하고, 간단한 검토 완료 메시지를 함께 반환한다. 향후에는 보고서의
논리적 일관성, 출처 표기, 요약 품질 등을 검토하여 수정 요청을 반환하는 기능을
추가할 수 있다.
"""

from src.state import ResearchState


def report_reviewer_node(state: ResearchState) -> ResearchState:
    """보고서를 검토하고 피드백을 추가한다.

    Args:
        state: 현재 그래프 상태. ``report_markdown`` 키에 최종 보고서를 담고 있어야 한다.

    Returns:
        검토 피드백을 담은 새 상태 사전. 기본 구현은 ``report_markdown``를 그대로
        유지하고 ``review_feedback`` 필드를 추가한다.
    """
    report = state.get("report_markdown", "")
    # 간단한 검토 메시지를 만든다. 향후에는 실제 내용 검토 로직을 추가할 수 있다.
    feedback = "보고서 검토 완료"
    return {
        "report_markdown": report,
        "review_feedback": feedback,
    }


__all__ = ["report_reviewer_node"]