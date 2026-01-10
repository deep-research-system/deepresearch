import json

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

from configuration import settings
from src.state import SummaryState, FinalReportState
from src.prompts.prompts import final_report_prompt


def llm_final_report():
    return init_chat_model(
        settings.llm_model,
        api_key=settings.openai,
        temperature=0.2,
        timeout=120,
        max_tokens=1800,
    )


def final_report_node(state: SummaryState) -> FinalReportState:
    """
    입력: SummaryState
      - doc_summaries: List[DocSummary]

    출력:
      - final_report: str (Markdown)
    """
    doc_summaries = state.get("doc_summaries")

    llm = llm_final_report()

    payload = {
        "doc_summaries": doc_summaries}

    user_input = (
        "다음 입력을 근거로 최종 보고서를 작성하라.\n\n"
        "문서 요약(doc_summaries):\n"
        f"{json.dumps(payload['doc_summaries'], ensure_ascii=False, indent=2)}\n"
    )

    messages = [
        SystemMessage(content=final_report_prompt),
        HumanMessage(content=user_input),
    ]

    res = llm.invoke(messages)
    markdown = res.content.strip()

    return {"final_report": markdown}