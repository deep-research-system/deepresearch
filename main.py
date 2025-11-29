from app.agent.unified_agent import create_unified_agent

def main():
    agent = create_unified_agent()

    print("무엇을 도와드릴까요? (계산, 날씨, 딥리서치 가능)")
    user_input = input("> ")

    result = agent.invoke({"input": user_input})

    print("\n=== 에이전트 응답 ===")
    print(result["output"])


if __name__ == "__main__":
    main()
