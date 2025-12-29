from src.agents.clarify import clarify

def run(question: str):
    state = {"question": question}
    out = clarify(state)
    print("========= 질문 =========")
    print(question)
    print("=== 답변 날 것===")
    print(out.get("streaming_text"))
    print("\n")

if __name__ == "__main__":
    run("   ")                 
    run("....")
    run("페이커")
    run("엔비디아")