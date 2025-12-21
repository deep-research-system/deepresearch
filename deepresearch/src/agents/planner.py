"""검색 지향 서브 쿼리를 생성하는 에이전트.

이 플래너는 연구 질문을 분석하여 웹 검색에 적합한 간결한 질의 목록을 생성한다.
언어 모델을 사용하여 질문을 해석하고, 서브 쿼리가 주제의 다양한 측면을 중복 없이 포괄하도록 한다.
"""

from typing import List
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

from configuration import settings


# 플래너의 역할을 설명하는 시스템 프롬프트. 이 프롬프트를 조정하여 플래너의 동작을 미세 조정할 수 있다.
SYSTEM_PROMPT = (
    "너는 딥리서치 플래너다.\n"
    "사용자 질문을 웹검색에 적합한 하위 질의(sub-queries)로 분해한다.\n"
    "- 한국어 질문이면 한국어/영어를 섞어도 된다(검색 효율 우선).\n"
    "- 중복/유사 질의는 제거한다.\n"
    "- 출력은 반드시 '줄바꿈으로 구분된 질의 목록'만 출력한다."
)


def plan_subqueries(question: str) -> List[str]:
    """주어진 연구 질문에 대한 서브 쿼리 목록을 생성한다.

    Args:
        question: 사용자의 연구 질문.

    Returns:
        웹 검색에 적합한, 중복이 제거된 서브 쿼리 목록을 반환한다.
    """
    # Initialize the chat model with the configured parameters
    llm = init_chat_model(
        settings.llm_model,
        temperature=settings.temperature,
        timeout=30,
        max_tokens=400,
    )
    # Compose the chat messages
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"질문: {question}\n최대 {settings.max_subqueries}개로 생성해."),
    ]
    # Invoke the model to get the raw text response
    text = llm.invoke(messages).content.strip()
    # Split lines and clean up list items
    raw = [line.strip("-• \t") for line in text.splitlines() if line.strip()]
    dedup: List[str] = []
    seen: set[str] = set()
    for q in raw:
        key = q.lower()
        if key not in seen:
            seen.add(key)
            dedup.append(q)
        if len(dedup) >= settings.max_subqueries:
            break
    return dedup


__all__ = ["plan_subqueries"]