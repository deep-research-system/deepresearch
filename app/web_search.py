# 1. 질문을 하면 그 질문에 대한 서브 쿼리를 3개로 만듦
#   (즉, 질문과 비슷한 유형 3개 만들어서 검색)
# 2. 크롤링 단계에서 순차적으로 처리하는게 아니라 병렬처리(현재 5개씩)를 해서 속도 빠르게 함

### 서브 쿼리를 몇개로 하고 어떠한 방식으로 서브 쿼리 만들지(프롬프트 세세히) 추가적인 구상 필요
### 병렬처리를 몇 개로 할 지 등 세부적인 설정 작업 추가적으로 필요

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import json
from .api import fc, call_llm

# 검색 관련 기본 설정
SEARCH_LIMIT_PER_QUERY = 6  # firecrawl search limit
MAX_WORKERS = 5             # 동시에 크롤링할 쓰레드 수


# 세부 쿼리 만드는 부분
def generate_subqueries(topic: str) -> List[str]:
    """
    사용자의 리서치 주제(topic)를 입력받아,
    웹 검색에 사용할 3개의 세부 검색 쿼리를 LLM으로부터 생성한다.
    init_chat_model 기반 call_llm을 사용한다.
    """
    system_prompt = "너는 웹 리서치용 검색어를 만들어주는 도우미야."

    user_content = f"""
너는 웹 리서치용 검색어를 만들어주는 도우미야.

사용자의 리서치 주제:
"{topic}"

이 주제를 더 정확하게 조사하기 위해,
서로 다른 관점과 세부 정보를 가져올 수 있는 한국어 검색 쿼리를 3개 만들어라.

출력 형식은 반드시 아래 JSON 형식만 사용해라.

[
  "첫 번째 검색 쿼리",
  "두 번째 검색 쿼리",
  "세 번째 검색 쿼리"
]

설명, 문장, 해설 없이 JSON만 출력해라.
"""


    content = call_llm(
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=0.3,
        max_tokens=400,
    )

    try:
        data = json.loads(content)
        subqueries = [q for q in data if isinstance(q, str) and q.strip()]
        if not subqueries:
            return [topic]
        return subqueries
    except Exception:
        # LLM이 JSON 형식을 안 지켰을 때
        print("[경고] 서브 쿼리 JSON 파싱 실패, 원래 주제만 사용합니다.")
        return [topic]


# 검색 엔진을 통해 검색 하여 URL 가져오는 과정
def search_web(topic: str) -> List[str]:
    """
    1) 사용자의 질문(topic)으로부터 LLM이 여러 개의 검색 쿼리를 생성
    2) 각 쿼리로 Firecrawl 검색
    3) URL들을 중복 없이 모아서 반환
    """
    subqueries = generate_subqueries(topic)

    print("\n[1/3-1] 생성된 검색 쿼리들:")
    for i, q in enumerate(subqueries, start=1):
        print(f"  {i}. {q}")

    all_urls: List[str] = []
    seen = set()

    # 각 서브 쿼리로 Firecrawl search
    for q in subqueries:
        try:
            result = fc.search(query=q, limit=SEARCH_LIMIT_PER_QUERY)
        except Exception as e:
            print(f"[검색 에러] '{q}' 쿼리에서 오류 발생: {e}")
            continue

        web_results = getattr(result, "web", []) or []

        for item in web_results:
            url = getattr(item, "url", None)
            if url and url not in seen:
                seen.add(url)
                all_urls.append(url)

    print(f"\n[1/3-2] 서브 쿼리 통합 후 최종 URL 개수: {len(all_urls)}")
    return all_urls

# 가져온 URL을 통해 크롤링을 어떠한 방식으로 할건지의 부분
def scrape_single(url: str) -> Optional[Dict]:
    """URL 하나를 크롤링해서 dict로 돌려주는 함수"""
    try:
        page = fc.scrape(url, formats=["markdown"])

        if hasattr(page, "markdown"):
            text = page.markdown or ""
            metadata = getattr(page, "metadata", None)
            if isinstance(metadata, dict):
                title = metadata.get("title", "") or ""
            else:
                title = ""
        elif isinstance(page, dict):
            data = page.get("data") or page
            text = data.get("markdown", "") or ""
            meta = data.get("metadata", {}) or {}
            title = meta.get("title", "") or ""
        else:
            text = ""
            title = ""

        if text.strip():
            return {
                "url": url,
                "title": title,
                "text": text,
            }
        else:
            print(f"[스크랩 경고] {url} - 내용이 비어 있음")
            return None

    except Exception as e:
        print(f"[스크랩 에러] {url} - {e}")
        return None

# 크롤링을 n개씩 병렬처리 하는 부분
def scrape_pages(urls: List[str]) -> List[Dict]:
    """여러 URL을 병렬로 크롤링해서 문서 리스트로 반환"""
    documents: List[Dict] = []

    print(f"  - 스크랩 대상 URL 개수: {len(urls)}")

    # 병렬 실행
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scrape_single, url): url for url in urls}

        for i, future in enumerate(as_completed(futures), start=1):
            doc = future.result()
            if doc:
                documents.append(doc)
                print(f"  - 스크랩 성공 {len(documents)}개")

    return documents
