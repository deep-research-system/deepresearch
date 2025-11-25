# .env에 따로 API 목록 만들고
# 여기서는 필요한 API만 가져와서 연결함



import os
from groq import Groq
from firecrawl import Firecrawl

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

if not GROQ_API_KEY:
    print("GROQ_API_KEY 환경변수가 설정되어 있지 않습니다.")
if not FIRECRAWL_API_KEY:
    print("FIRECRAWL_API_KEY 환경변수가 설정되어 있지 않습니다.")

# Groq LLM, Firecrawl 클라이언트
client = Groq(api_key=GROQ_API_KEY)
fc = Firecrawl(api_key=FIRECRAWL_API_KEY)
