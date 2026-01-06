from typing import TypedDict, List, Annotated, Optional


class BaseState(TypedDict, total = False):
    """
    프론트에서 들어오는 것들 모음
    """
    question: Annotated[str, "기준이될 사용자 입력"]
    addition_questions: Annotated[List[str], "추가질문 리스트"]
    addition_questions_answers: Annotated[List[str], "사용자가 답한 추가질문"]


class ClarifyState(TypedDict, total = False):
    error_messages: Annotated[str, "잘못된 질문 입력에대한 LLM의 답변"]
    need_addition_questions: Annotated[bool, "추가 질문 필요 여부"]
    qna_ment: Annotated[str, "추가질문 안내문구"]
    answers_sufficient: Annotated[bool, "추가질문에 대한 답변 판단"]
    final_question: Annotated[str, "확정된 최종 질문"]


class SubqueryState(TypedDict, total = False):
    subqueries: Annotated[List[str], "웹검색용 질문들(서브쿼리)"]

class SearchResult(TypedDict):
    """
    query: 쿼리이름
    title: 제목
    url: url
    snippet: 짧은 요약문
    score: 검색어 관련성 점수
    source: 검색엔진
    """
    query: str
    title: str
    url: str
    snippet: str | None
    score: float | None
    source: str

class SearchState(TypedDict, total=False):
    search_results: Annotated[List[SearchResult], "웹검색 결과 리스트"]


class DocSummary(TypedDict):
    """
    검색별 문서요약(낱개)
    """
    query: Annotated[str, "검색에 사용된 서브쿼리"]
    title: Annotated[str, "원본 문서 제목"]
    url: Annotated[str, "원본 문서 URL"]
    source: Annotated[str, "문서 수집 출처"]
    score: Annotated[Optional[float], "검색 엔진 relevance 점수"]
    summary: Annotated[str, "문서 요약 본문"]


class SummaryState(TypedDict, total=False):
    """
    문서 요약 묶음
    """
    doc_summaries: Annotated[List[DocSummary], "문서별 요약 결과 리스트"]
    
    
# graph.py용
class ResearchState(BaseState, ClarifyState, SubqueryState, SearchState, SummaryState, total=False):
    pass