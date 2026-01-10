import json
import asyncio
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from configuration import settings
from src.state import SearchState, SummaryState, DocSummary
from src.prompts.prompts import summary_prompt


def llm_summary():
    return init_chat_model(
        settings.llm_model,
        api_key=settings.openai,
        temperature=0.2,
        max_tokens=3000,
    )


def _debug_prompt_once():
    print("=== SUMMARY_PROMPT CHECK ===")
    print(summary_prompt)
    print("HAS_H2:", "## 1) 한줄 요약" in summary_prompt)
    print("===========================")


async def summary_node(state: SearchState) -> SummaryState:
    llm = llm_summary()
    search_results = state.get("search_results") or []

    # 프롬프트 적용 여부 확인(노드 시작 시 1회)
    _debug_prompt_once()

    async def summarize_one(sr) -> DocSummary:
        query = sr.get("query")
        title = sr.get("title")
        url = sr.get("url")
        source = sr.get("source")
        score = sr.get("score")
        content = sr.get("content") or ""

        user_input = f"""
[검색 메타]
- query: {query}
- title: {title}
- url: {url}
- source: {source}
- score: {score}

[요약 대상 텍스트(content)]
{content}
""".strip()

        llm_sum = await llm.ainvoke([
            SystemMessage(content=summary_prompt),
            HumanMessage(content=user_input),
        ])

        llm_json = json.loads(llm_sum.content)

        return {
            "query": query,
            "title": title,
            "url": url,
            "source": source,
            "score": score,
            "summary": llm_json.get("summary"),
        }

    doc_summaries = await asyncio.gather(*(summarize_one(sr) for sr in search_results))
    return {"doc_summaries": doc_summaries}
