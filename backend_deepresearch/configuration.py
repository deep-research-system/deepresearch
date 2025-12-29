import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    openai = os.getenv("OPENAI_API_KEY")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    tavily = os.getenv("TAVILY_API_KEY")
    temperature = 0.5
    max_subqueries = 3

settings = Settings()
