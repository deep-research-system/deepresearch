


from app.web_search import search_web, scrape_pages
from app.summarize import ask_llm

def main():
    print("어떤 주제를 리서치하시겠습니까?")
    topic = input("> ")

    print("\n[1/3] 웹에서 자료 수집 중 (Search)...")
    urls = search_web(topic)
    print(f"  - 검색된 URL 개수: {len(urls)}")

    print("\n[2/3] 웹페이지 스크랩 중 (Scrape)...")
    docs = scrape_pages(urls)
    print(f"  - 스크랩 성공 문서 개수: {len(docs)}")

    print("\n[3/3] 보고서 생성 중 (LLM)...")
    report = ask_llm(topic, docs)

    print("\n=== 생성된 리서치 보고서 ===\n")
    print(report)


if __name__ == "__main__":
    main()
