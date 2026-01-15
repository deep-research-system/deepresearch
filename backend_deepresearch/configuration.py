import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    openai = os.getenv("OPENAI_API_KEY")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    tavily = os.getenv("TAVILY_API_KEY")
    temperature = 0.3

settings = Settings()


default_report_structure: str = """사용자가 제공한 주제로 보고서를 작성할 때 아래 구조를 사용하라:

1. 서론(리서치 불필요)
   - 주제 영역에 대한 간단한 개요

2. 본문 섹션들:
   - 각 섹션은 사용자가 제공한 주제의 하위 주제 하나에 집중

3. 결론
   - 본문 섹션들을 요약/응축하는 구조 요소 1개(리스트 또는 표)를 포함하는 것을 목표로 한다
   - 간결한 요약을 제공한다
"""