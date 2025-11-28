# web_search.py 에서 검색 및 크롤링을 한 후
# 1. 이 파일에서 그 내용을 가지고 1차 요약을 통한 후,
#    LLM에 그 요약문을 넣어 2차로 최종 보고서를 만들게끔 함

### 아직 요약을 어떠한 형태로 할건지 구상을 안해서 이 부분 해결 필요
### 각 단계에서 프롬프트 등 구상을 디테일 하게 만들 필요

from typing import List, Dict
from .api import call_llm


def summarize_single_doc(topic: str, doc: Dict) -> str:
    """
    단일 문서를 주제에 맞게 요약하는 함수 (map 단계).
    한 번에 너무 많은 텍스트를 보내지 않도록 앞부분만 사용.
    요약도 짧게(max_tokens 줄임).
    """
    text = doc.get("text", "")
    url = doc.get("url", "")
    title = doc.get("title", "")

    # 문서가 너무 길면 앞부분만 잘라서 사용
    snippet = text[:1500]

    system_prompt = ("당신은 신뢰도 높은 리서치 요약 전문가입니다. "
    "모든 요약은 사실 기반으로 작성하며, 과장하거나 추론을 덧붙이지 않습니다. "
    "요약 과정에서 반드시 사용자가 제공한 정보만 사용합니다.")

    user_content = f"""
당신은 아래 문서 내용을 바탕으로 '{topic}'과 관련된 핵심 정보만 요약해야 합니다.

주제: {topic}
문서 제목: {title}
출처 URL: {url}

아래 문서 내용 일부를 읽고, 다음 기준에 맞춰 요약하세요.

요약 시 지켜야 할 점:
- 주제와 직접 관련된 주장, 사실, 수치, 날짜, 고유명사 위주로 정리
- 3~5줄 정도의 한국어 문장으로 요약
- 각 줄 끝에 반드시 (출처: {url}) 를 붙일 것
- 제공된 문서 내용 외의 정보는 절대 추가하지 말 것


[문서 내용 일부]
{snippet}
"""

    summary = call_llm(
        system_prompt=system_prompt,
        user_content=user_content,
        max_tokens=250,
        temperature=0.2,
    )

    return summary.strip()

    return resp.choices[0].message.content


def ask_llm(topic: str, docs: List[Dict]) -> str:
    """
    맵-리듀스 형식:
    1) 각 문서를 개별적으로 요약 (summarize_single_doc)
    2) 요약들을 모아서 최종 보고서 생성
    최종 단계에서 토큰 초과가 나지 않도록 요약 개수와 길이를 제한.
    """
    if not docs:
        return "스크랩된 문서가 없어서 보고서를 생성할 수 없습니다."

    doc_summaries: List[str] = []

    # 요약을 생성할 최대 문서 개수 (최대 20까지 크롤링했어도 여기서 줄일 수 있음)
    MAX_DOCS_FOR_SUMMARY = 20       # 요약 생성용 상한
    MAX_DOCS_FOR_FINAL = 10         # 최종 보고서에 실제로 쓸 요약 개수
    MAX_MERGED_CHARS = 9000         # 최종 프롬프트에 넣을 요약 전체 문자 수 상한

    print("\n[3/3-1] 문서별 요약 생성 중...")
    for i, d in enumerate(docs):
        if i >= MAX_DOCS_FOR_SUMMARY:
            break

        url = d.get("url", "")
        print(f"  - 문서 {i+1} 요약 중... (출처: {url})")
        summary = summarize_single_doc(topic, d)
        doc_summaries.append(f"[문서 {i+1}] {url}\n{summary}\n")

    if not doc_summaries:
        return "문서 요약에 실패하여 보고서를 생성할 수 없습니다."

    # 최종 보고서에 사용할 요약 개수 제한
    selected_summaries = doc_summaries[:MAX_DOCS_FOR_FINAL]
    merged_summaries = "\n\n".join(selected_summaries)

    # 전체 길이가 너무 길면 자르기 (문자 기준, 대략 토큰 수 줄이는 효과)
    if len(merged_summaries) > MAX_MERGED_CHARS:
        merged_summaries = merged_summaries[:MAX_MERGED_CHARS]

    print("\n[3/3-2] 최종 보고서 생성 중 (LLM)...")

    system_prompt = "당신은 신뢰도 높은 리서치 분석가입니다."


    user_content  = f"""
당신은 전문 리서처입니다.

아래는 '{topic}'에 대해 여러 웹 문서에서 추출한 요약 모음입니다.
이 요약들을 기반으로 전체 주제를 통합적으로 분석한 보고서를 작성하세요.

[보고서 구성]
1. 주제 개요
2. 주요 이슈 요약
3. 핵심 사실(날짜, 수치 포함)
4. 출처별 쟁점/의견 차이
5. 종합 결론

작성 시 규칙:
- 핵심 근거가 되는 문장에는 관련된 출처 URL을 괄호 안에 명시
  예: "삼성전자 2025년 전망은 긍정적이다. (출처: https://...)"
- 서로 다른 문서에서 상반된 의견이 있으면, 각각 어떤 출처에서 나왔는지 구분해서 설명
- 전체적으로 보고서 형식(서론-본론-결론 느낌)으로 자연스럽게 작성

[문서 요약 모음]
{merged_summaries}
"""

    final_report = call_llm(
        system_prompt=system_prompt,
        user_content=user_content,
        max_tokens=1000,
        temperature=0.3,
    )

    return final_report.strip()
