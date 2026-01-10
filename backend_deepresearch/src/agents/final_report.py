import json

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

from configuration import settings
from src.state import SummaryState, FinalReportState, ResearchState
from src.prompts.prompts import final_report_prompt


def llm_final_report():
    return init_chat_model(
        settings.llm_model,
        api_key=settings.openai,
        temperature=0.2,
        timeout=120,
    )


def final_report_node(state: ResearchState) -> FinalReportState:
    doc_summaries = state.get("doc_summaries")
    final_question = state.get("final_question")

    llm = llm_final_report()

    payload = {
        "final_question": final_question,
        "doc_summaries": doc_summaries}

    user_input = (
        "다음 입력을 근거로 최종 보고서를 작성하라.\n\n"
        f"최종 질문(final_question): {payload['final_question']}\n\n"
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