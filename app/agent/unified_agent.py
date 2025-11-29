# app/agent/unified_agent.py

from typing import Dict, Any

from langchain.chat_models import init_chat_model

from app.tools.calculator_tool import calculator
from app.tools.weather_tool import weather
from app.tools.research_tool import deep_research


class UnifiedAgent:
    """
    LangChain agents 모듈에 의존하지 않고,
    LLM + 우리가 직접 만든 router 로직으로 동작하는 간단한 에이전트.
    """

    def __init__(self):
        # 라우팅 및 최종 답변용 LLM
        self.llm = init_chat_model(
            "llama-3.1-8b-instant", 
            model_provider="groq",
            temperature=0.1,
            max_tokens=1000,
        )

    def _route_tool(self, user_input: str) -> str:
        """
        LLM에게 '어떤 도구를 쓸지'만 판단하게 하는 라우팅 함수.
        calculator / weather / deep_research 중 하나만 출력하게 함.
        """
        routing_prompt = f"""
너는 사용자의 요청을 보고 어떤 도구를 쓸지 결정하는 라우터야.

사용 가능한 도구:
- calculator : 수학 계산, 수식 계산, 간단한 숫자 연산
- weather    : 특정 도시의 날씨, 기온, 비/눈, 기상 정보
- deep_research : 그 외 모든 정보 요청, 분석, 설명, 요약, 보고서 작성 등

규칙:
1. 사용자가 수식을 입력하거나 "계산", "얼마야", "몇 퍼센트" 같이
   명확한 수학 계산이면 calculator 를 선택해.
2. 사용자가 "날씨", "기온", "기상", "비 와?", "눈 와?" 같이
   날씨 관련 질문을 하면 weather 를 선택해.
3. 그 외의 모든 질문은 무조건 deep_research 를 선택해.

반드시 아래 중 하나의 단어만 출력해:
calculator
weather
deep_research

사용자 입력: {user_input}
"""

        result = self.llm.invoke(routing_prompt)
        tool_name = str(result).strip().lower()

        if "calculator" in tool_name:
            return "calculator"
        if "weather" in tool_name:
            return "weather"
        # 기본값: deep_research
        return "deep_research"

    def _call_tool(self, tool_name: str, user_input: str) -> str:
        """
        실제 툴을 호출하는 부분.
        @tool 데코레이터를 쓴 객체이기 때문에 .run() 또는 .invoke()를 사용.
        """
        try:
            if tool_name == "calculator":
                # calculator(expression: str) -> str
                if hasattr(calculator, "invoke"):
                    return calculator.invoke(user_input)  # 새로운 버전
                elif hasattr(calculator, "run"):
                    return calculator.run(user_input)     # 예전 버전
                else:
                    return calculator(user_input)         # 혹시 함수 그대로인 경우

            elif tool_name == "weather":
                # weather(city: str) -> str
                if hasattr(weather, "invoke"):
                    return weather.invoke(user_input)
                elif hasattr(weather, "run"):
                    return weather.run(user_input)
                else:
                    return weather(user_input)

            else:  # deep_research
                # deep_research(topic: str) -> str
                if hasattr(deep_research, "invoke"):
                    return deep_research.invoke(user_input)
                elif hasattr(deep_research, "run"):
                    return deep_research.run(user_input)
                else:
                    return deep_research(user_input)

        except Exception as e:
            return f"도구 실행 중 오류가 발생했습니다: {e}"

    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangChain 스타일을 흉내낸 인터페이스.
        main.py에서 agent.invoke({'input': ...}) 형식으로 사용할 수 있게 맞춘 것.
        """
        user_input = inputs.get("input", "")
        if not user_input:
            return {"output": "입력이 비어 있습니다."}

        # 1) 어떤 도구를 쓸지 라우팅
        tool_name = self._route_tool(user_input)

        # 2) 해당 도구 호출
        tool_result = self._call_tool(tool_name, user_input)

        # 3) 최종 답변 포맷 (원하면 여기서 한 번 더 LLM으로 다듬을 수도 있음)
        return {
            "output": f"[사용된 도구: {tool_name}]\n\n{tool_result}"
        }


def create_unified_agent() -> UnifiedAgent:
    """main.py에서 불러 쓸 에이전트 생성 함수."""
    return UnifiedAgent()
