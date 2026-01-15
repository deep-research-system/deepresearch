from typing import List, Optional, TypedDict, Annotated

class ReportSection(TypedDict, total=False):
    name: Annotated[str, "섹션 이름"]
    description: Annotated[str, "섹션 설명"]
    research: Annotated[bool, "웹 리서치 필요 여부"]
    content: Annotated[str, "섹션 내용"]

class PlannerState(TypedDict, total=False):
    topic: Annotated[str, "사용자의 질문"]
    queries: Annotated[List[str], "만들어진 서브쿼리들"]
    sections: Annotated[List[ReportSection], "보고서 골조"]
    feedback: Annotated[Optional[str], "사용자 피드백"]
    approved: Annotated[Optional[bool], "사용자 승인 여부"]