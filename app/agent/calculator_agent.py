# 지울거같음 일단 남겨둠둠

from langchain.chat_models import init_chat_model
from langchain.agents import create_react_agent
from langchain.agents import AgentExecutor
from app.agent.calculator_tool import calculator

def create_calculator_agent():
    llm = init_chat_model(
        "groq/llama-3.1-8b-instant",
        temperature=0.0
    )

    tools = [calculator]

    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt="너는 계산 전문가야. 계산이 필요하면 반드시 calculator 도구를 사용해라."
    )

    executor = AgentExecutor(agent=agent, tools=tools)
    return executor


def run_calculator_cli():
    print("계산할 식을 입력하세요:")
    expr = input("> ")

    agent = create_calculator_agent()
    result = agent.invoke({"input": expr})

    print("\n=== 결과 ===")
    print(result["output"])