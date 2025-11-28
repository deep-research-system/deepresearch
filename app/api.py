# .env에 따로 API 목록 만들고
# 여기서는 필요한 API만 가져와서 연결함

import os
from typing import Optional, List


from groq import Groq
from firecrawl import Firecrawl

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage



try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGSMITH_API_KEY")

if not GROQ_API_KEY:
    print("GROQ_API_KEY 환경변수가 설정되어 있지 않습니다.")
if not FIRECRAWL_API_KEY:
    print("FIRECRAWL_API_KEY 환경변수가 설정되어 있지 않습니다.")
if not LANGCHAIN_API_KEY:
    print("LANGCHAIN_API_KEY 환경변수가 설정되어 있지 않습니다.")

# Groq LLM, Firecrawl 클라이언트
client = Groq(api_key=GROQ_API_KEY)
fc = Firecrawl(api_key=FIRECRAWL_API_KEY)

# 다용도로 활용할 수 있는 LLM 
def get_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    timeout: Optional[int] = None,
    max_tokens: Optional[int] = None,
) -> BaseChatModel:
    """
    LangChain의 init_chat_model을 사용해서 Groq LLM을 생성하는 함수.
    기본값은 환경변수(.env)에서 읽고, 인자로 전달하면 덮어쓴다.

    .env 예시:
        LLM_MODEL_NAME=groq:llama-3.1-8b-instant
        LLM_TEMPERATURE=0.3
        LLM_TIMEOUT=30
        LLM_MAX_TOKENS=4000
    """

    # 모델 이름: 인자 > 환경변수 > 기본값
    model_name = model or os.getenv("LLM_MODEL_NAME", "groq:llama-3.1-8b-instant")

    kwargs: dict = {}

    # temperature
    if temperature is not None:
        kwargs["temperature"] = temperature
    else:
        env_temp = os.getenv("LLM_TEMPERATURE")
        if env_temp is not None:
            kwargs["temperature"] = float(env_temp)

    # timeout
    if timeout is not None:
        kwargs["timeout"] = timeout
    else:
        env_timeout = os.getenv("LLM_TIMEOUT")
        if env_timeout is not None:
            kwargs["timeout"] = int(env_timeout)

    # max_tokens
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    else:
        env_max_tokens = os.getenv("LLM_MAX_TOKENS")
        if env_max_tokens is not None:
            kwargs["max_tokens"] = int(env_max_tokens)

    llm = init_chat_model(
        model_name,  # 예: "groq:llama-3.1-8b-instant"
        **kwargs,
    )

    return llm

# 간단한 유저질문응답 LLM
def call_llm(
    system_prompt: str,
    user_content: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    timeout: Optional[int] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    기존 Groq client.chat.completions.create(...) 한 번 호출하던 패턴을
    init_chat_model 기반으로 래핑한 함수.

    - system_prompt: 시스템 메시지
    - user_content: 유저 질문/입력
    """
    llm = get_llm(
        model=model,
        temperature=temperature,
        timeout=timeout,
        max_tokens=max_tokens,
    )

    messages: List[BaseMessage] = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    response = llm.invoke(messages)
    return response.content


# 필요하다면 기본 LLM 인스턴스도 만들어 둘 수 있다.
default_llm: BaseChatModel = get_llm()