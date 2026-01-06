import json
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from configuration import settings
from src.state import SearchState, SummaryState, DocSummary
from src.prompts.prompts import summary_prompt
import asyncio


def llm_summary():
    return init_chat_model(
        settings.llm_model,
        api_key=settings.openai,
        temperature=0.2,
        timeout=60,
        max_tokens=600,
    )
    
async def summary_node(state: SearchState) -> SummaryState:
    """
    입력:
      state["search_results"]: List[SearchResult]
        - query, title, url, snippet, score, source

    출력:
      {"doc_summaries": [...]}
    """
    llm = llm_summary()

    search_results = state.get("search_results")
    
    async def summary(sr) -> DocSummary:
        query = sr.get("query")
        title = sr.get("title")
        url = sr.get("url")
        source = sr.get("source")
        score = sr.get("score")  # Optional[float]
        snippet = sr.get("snippet")          # 개발과정은 snippet 실제는 content로
    
        # 문서 1개 기준으로 LLM 입력을 문자열로 구성
        user_input = f"""
        [검색 메타]
        - query: {query}
        - title: {title}
        - url: {url}
        - source: {source}
        - score: {score}

        [요약 대상 텍스트(snippet)]
        {snippet}""".strip()
                
        llm_sum = await llm.ainvoke([
            SystemMessage(content=summary_prompt),
            HumanMessage(content=user_input)])
        
        llm_json = json.loads(llm_sum.content)
                
        return {
            "query": query,
            "title": title,
            "url": url,
            "source": source,
            "score": score,
            "summary": llm_json.get("summary")}

    tasks = [summary(sr) for sr in search_results]
    doc_summaries = await asyncio.gather(*tasks)

    
    return {"doc_summaries": doc_summaries}
